from django.shortcuts import render
import logging
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.http import HttpResponse
import pandas as pd

# Create your views here.


def uploadcsv(request):
    """
    Current Issues:

    """
    data = {}
    if "GET" == request.method:
        return render(request, "cleancsv/upload_csv.html", data)
    try:
        csv_file = request.FILES["csv_file"]
        if not csv_file.name.endswith('.csv'):
            messages.error(request, 'File is not CSV type')
            return HttpResponseRedirect(reverse("cleancsv:upload_csv"))
            # if file is too large, return
        if csv_file.multiple_chunks():
            messages.error(request, "Uploaded file is too big (%.2f MB)." % (csv_file.size / (1000 * 1000),))
            return HttpResponseRedirect(reverse("cleancsv:upload_csv"))

        # file_data = csv_file.read().decode("utf-8")

        # point to file location.
        df = pd.read_csv(csv_file)
        df.columns = [i.lower().replace(' ', '_') for i in df.columns]  # lower case and replace spaces
        df.index += 2  # so when it says "check these lines" the numbers match with csv
        df = df.dropna(how='all')  # removes rows that are completely empty

        # get email list
        email_list = df['email']

        # Order columns so if rows needs to merge it is done properly
        cols = list(df)

        if 'first_name' in cols:
            cols.insert(0, cols.pop(cols.index('first_name')))
        else:
            print('No first_name column. Exiting...')
            exit()

        if 'last_name' in cols:
            cols.insert(1, cols.pop(cols.index('last_name')))
        else:
            print('No last_name column. Exiting...')
            exit()

        if 'email' in cols:
            cols.insert(2, cols.pop(cols.index('email')))
        else:
            print('No email column. Exiting...')
            exit()

        if (email_list.str.contains(',')).any():
            # splits email list so that everything before comma is put in email and the rest into secondary_email
            df[['email', 'secondary_email']] = email_list.str.split(',', 1).apply(pd.Series)

            df.columns = df.columns.fillna('secondary_email')

            if 'second_contact_email' in df.columns:  # this handles in case they do have the 'second_contact_email' column
                # Merges secondary_email into the 'second_contact_email' column
                df['second_contact_email'] = df['second_contact_email'].astype(str) + ',' + df['secondary_email']
                df = df.iloc[:, :-1]  # drops last column so there isn't double 'second_contact_email'

            df.rename(columns={'secondary_email': 'second_contact_email'}, inplace=True)
        else:
            if 'second_contact_email' not in df.columns:
                df['second_contact_email'] = ''

        # validate email and move bad ones
        df['second_contact_email'] = df[~df['email'].str.contains(pat=r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', case=False, na=False)][
            'email']
        df['email'] = df[df['email'].str.contains(pat=r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', case=False, na=False)]['email']

        # this adds 'second_contact_phone' in case they do not have the column
        phone_value = ''
        if 'second_contact_phone' not in df:
            df.loc[:, 'second_contact_phone'] = phone_value

        # only keep numbers in phone column
        df['phone'] = df['phone'].replace('[^0-9]+', '', regex=True)

        # moves phone numbers less than 8 and greater than 15 digits then removes them from phone
        df['second_contact_phone'] = df[~df['phone'].astype(str).str.contains(pat=r'^(?:(?!^.{,7}$|^.{16,}$).)*$', case=False, na=False)]['phone']
        df['phone'] = df[df['phone'].astype(str).str.contains(pat=r'^(?:(?!^.{,7}$|^.{16,}$).)*$', case=False, na=False)]['phone']

        # needed for below merger. Gets column headers
        get_col_headers = str(list(df))
        # gets rid of [''] around header names
        col_headers = eval(get_col_headers)

        # searches column named email and drops duplicates but keeps the first one and merges data
        # https://github.com/khalido/notebooks/blob/master/pandas-dealing-with-dupes.ipynb
        df["first_dupe"] = df.duplicated("email", keep=False) & ~df.duplicated("email", keep="first")

        def combine_rows(row, key="email", cols_to_combine=col_headers[3:]):
            """takes in a row, looks at the key column
                if its the first dupe, combines the data in cols_to_combine with the other rows with same key
                needs a dataframe with a bool column first_dupe with True if the row is the first dupe"""

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
        df.drop_duplicates(subset=["email"], inplace=True)
        df.groupby('email').agg(lambda x: ", ".join(x)).reset_index()
        del df['first_dupe']

        # gets rid of random nan that pops up sometimes
        df = df.replace('(?:^|\W)nan(?:$|\W)', '', regex=True)

        # Convert names back from ex. first_name so system auto catches it
        df.columns = [i.title().replace('_', ' ') for i in df.columns]
        print("Bottom of pandas stuff.")
        done = df.to_csv(index=False)

        response = HttpResponse(done, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="done.csv"'
        return response

    except Exception as e:
        logging.getLogger("error_logger").error("Unable to upload file. " + repr(e))
        messages.error(request, "Unable to upload file. " + repr(e))

    return HttpResponseRedirect(reverse("cleancsv:upload_csv"))
