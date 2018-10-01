from django.shortcuts import render
import logging
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.http import HttpResponse
import time
import pandas as pd


# Create your views here.


def uploadcsv(request):
    data = {}
    if "GET" == request.method:
        return render(request, "cleancsv/upload_csv.html", data)
    try:
        csv_file = request.FILES["csv_file"]
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'File is not CSV type', extra_tags='alert')
            return HttpResponseRedirect(reverse("cleancsv:upload_csv"))
            # if file is too large, return
        if csv_file.multiple_chunks():
            messages.error(request, "Uploaded file is too big (%.2f MB)." % (csv_file.size / (1000 * 1000),), extra_tags='alert')
            return HttpResponseRedirect(reverse("cleancsv:upload_csv"))

        """
        https://stackoverflow.com/questions/32787838/how-to-pass-data-between-django-views
        Current Issues:
        2. If not first_name and last_name then find name to split it - if full name and not fist and last then
            - Look for FirstName or something
        2. if not phone look for mobile_phone or phone_number or something
        2. if not email look for email address or something
        1. makes sec contact email and phone sometimes when its not needed
        """

        start_time = time.time()
        # point to file location.
        df = pd.read_csv(csv_file)
        df.columns = [i.lower().replace(' ', '_') for i in df.columns]  # lower case and replace spaces
        df.index += 2  # so when it says "check these lines" the numbers match with csv
        df = df.dropna(how='all')  # removes rows that are completely empty

        cols = list(df)
        if 'email' not in cols:
            if 'email_address' in cols:
                df.rename(columns={'email_address': 'email'}, inplace=True)
            elif 'emailaddress' in cols:
                df.rename(columns={'emailaddress': 'email'}, inplace=True)
            else:
                print("What are these peoples emails!?")


        # Checks for duplicate emails. May not be needed now.
        email_list = df['email']
        email_counts = email_list.value_counts()
        duplicate_emails = list(email_counts[email_counts > 1].index)
        # print(f'Check these emails for duplicates: {duplicate_emails}')

        # Prints the lines where phone len is less than 8 or greater than 15. May not be needed now.
        phone_list = df['phone']
        phone_list = phone_list.replace('[^0-9]+', '', regex=True)  # remove special characters
        phone_len = phone_list.astype(str).str.len()  # had to add .astype(str) before .str in order for certain csvs to work
        phone_bad = list(phone_len[(phone_len > 0) & (phone_len < 8) | (phone_len > 15)].index)
        # print(f'Check these lines for an incomplete phone number: {phone_bad}')


        # if no first_name and last_name column then we look for the "name" column and split it
        # not sure if this is the best way
        # keeping name column for now to be safe.
        if 'first_name' and 'last_name' not in cols:
            if 'firstname' and 'lastname' in cols:
                df.rename(columns={'firstname': 'first_name', 'lastname': 'last_name'}, inplace=True)
            elif 'name' in cols:
                df[['first_name', 'last_name']] = df.name.str.split(' ', 1, expand=True)
            else:
                print("Who are these people!?")


        if 'phone' not in cols:
            if 'phone_number' in cols:
                df.rename(columns={'phone_number': 'phone'}, inplace=True)
            elif 'mobile_phone' in cols:
                df.rename(columns={'mobile_phone': 'phone'}, inplace=True)
            else:
                print("What are these peoples numbers!?")


        if (df['email'].str.contains(',')).any():
            df['secondary_email'] = None
            df.columns = df.columns.fillna('secondary_email')

            # splits email list so that everything before comma is put in email and the rest into secondary_email
            df['email'], df['secondary_email'] = df['email'].str.split(',', 1).str

            if 'second_contact_email' in cols:  # this handles in case they do have the 'second_contact_email' column
                # Merges secondary_email into the 'second_contact_email' column
                df['second_contact_email'] = df['second_contact_email'].fillna('') + ', ' + df['secondary_email'].fillna('')
                # this is to just clean up column (i.e. remove leadning what space and random extra commas from merge)
                df['second_contact_email'] = df['second_contact_email'].replace('((, )$|[,]$)|(^\s)', '', regex=True)

                df = df.iloc[:, :-1]  # drops last column so there isn't double 'second_contact_email'

            df.rename(columns={'secondary_email': 'second_contact_email'}, inplace=True)
        else:
            pass


        # validate email and move bad ones
        df['temp_second_contact_email'] = df[~df['email'].str.contains(pat=r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', case=False, na=False)]['email']
        df['email'] = df[df['email'].str.contains(pat=r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', case=False, na=False)]['email']
        # merges columns so original second_contact_email doesn't get replaced by temp_second_contact_email
        df['second_contact_email'] = df['second_contact_email'].fillna('') + ', ' + df['temp_second_contact_email'].fillna('')
        del df['temp_second_contact_email']
        # this is to just clean up column (i.e. remove leadning what space and random extra commas from merge)
        df['second_contact_email'] = df['second_contact_email'].replace('((, )$|[,]$)|(^\s)', '', regex=True)


        # only keep numbers in phone column
        df['phone'] = df['phone'].replace('[^0-9]+', '', regex=True)

        # moves phone numbers less than 8 and greater than 15 digits then removes them from phone
        df['temp_second_contact_phone'] = df[~df['phone'].astype(str).str.contains(pat=r'^(?:(?!^.{,7}$|^.{16,}$).)*$', case=False, na=False)]['phone']
        df['phone'] = df[df['phone'].astype(str).str.contains(pat=r'^(?:(?!^.{,7}$|^.{16,}$).)*$', case=False, na=False)]['phone']

        # merges columns so original second_contact_email doesn't get replaced by temp_second_contact_email
        df['second_contact_phone'] = df['second_contact_phone'].astype(str).fillna('') + ', ' + df['temp_second_contact_phone'].astype(str).fillna('')
        del df['temp_second_contact_phone']
        # this is to just clean up column (i.e. remove leadning what space, random extra commas from merge, and random .0)
        df['second_contact_phone'] = df['second_contact_phone'].replace('((, )$|[,]$|(^\s)|(\.0)$)', '', regex=True)


        # needed for below merger. Gets column headers
        get_col_headers = str(list(df))
        # gets rid of [''] around header names
        col_headers = eval(get_col_headers)

        # searches column named email and drops duplicates but keeps the first one and merges data
        # https://github.com/khalido/notebooks/blob/master/pandas-dealing-with-dupes.ipynb
        df["first_dupe"] = df.duplicated("email", keep=False) & ~df.duplicated("email", keep="first")

        def combine_rows(row, key="email", cols_to_combine=col_headers[3:]):
            # takes in a row, looks at the key column if its the first dupe, combines the data in cols_to_combine with the other rows with same key
            # needs a dataframe with a bool column first_dupe with True if the row is the first dupe

            if row['first_dupe'] is True:
                # making a df of dupes item
                dupes = df[df[key] == row[key]]

                # skipping the first row, since thats our first_dupe
                for i, dupe_row in dupes.iloc[1:].iterrows():
                    for col in cols_to_combine:
                        dupe_row[col] = str(dupe_row[col])
                        row[col] = str(row[col])
                        row[col] += ", " + dupe_row[col]
                # make sure first_dupe doesn't get processed again
                row.first_dupe = False
            return row


        df = df.apply(combine_rows, axis=1, result_type=None)
        # drops dup emails but keep first instance since everything should have been merged into that but ignores cells that are empty because
        # before it would just delete all rows with an empty email cell but the first one.....
        df = df[df['email'].isnull() | ~df[df['email'].notnull()].duplicated(subset='email',keep='first')]
        df.groupby('email').agg(lambda x: ", ".join(x)).reset_index()
        del df['first_dupe']

        # gets rid of random nan that pops up sometimes
        df = df.replace('(?:^|\W)nan(?:$|\W)', '', regex=True)


        # Convert names back from ex. first_name so system auto catches it
        df.columns = [i.title().replace('_', ' ') for i in df.columns]
        done = df.to_csv(index=False)

        end_time = time.time()
        runtime = end_time - start_time
        print(runtime)

        response = HttpResponse(done, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="done.csv"'
        return response

    except Exception as e:
        logging.getLogger("error_logger").error("Unable to upload file. " + repr(e))
        messages.error(request, "Unable to upload file. " + repr(e))

    return HttpResponseRedirect(reverse("cleancsv:upload_csv"))
