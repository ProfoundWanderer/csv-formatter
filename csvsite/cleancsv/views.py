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
            messages.error(request, "Uploaded file is too big. Make sure file is less than 2 MB. (%.2f MB)." % (csv_file.size / (1000 * 1000),), extra_tags='alert')
            return HttpResponseRedirect(reverse("cleancsv:upload_csv"))

            """
            - I have been told there is a 5 mb csv size limit so need to change the size limit on the site
            """

        start_time = time.time()
        # point to file location.
        df = pd.read_csv(csv_file)
        df.columns = [i.lower().replace(' ', '_') for i in df.columns]  # lower case and replace spaces
        df.index += 2  # so when it says "check these lines" the numbers match with csv
        # removes empty rows then empty columns
        df = df.dropna(how='all')
        df = df.dropna(axis=1, how='all')


        # comment this asap
        first_name_list = [
            'firstname',
            'primary_firstname',
            'lead_first_name',
            ]

        last_name_list = [
            'lastname',
            'primary_lastname',
            'lead_last_name',
            ]

        if 'first_name' and 'last_name' not in df.columns:
            if 'first_name' not in df.columns:
                tried_first_names = []
                for key in first_name_list:
                    try:
                        df.rename(columns={key: 'first_name'}, inplace=True)
                        if 'first_name' not in df.columns:
                            tried_first_names.append(key)
                            if len(tried_first_names) == 3:
                                try:
                                    df = df.rename(columns={df.filter(like='firstname').columns[0]: 'first_name'})
                                except IndexError:
                                    # pass so can check if there is a 'name' column
                                    pass
                        else:
                            break
                    except:
                        raise IndexError("No columns match values in first_name_list")
            if 'first_name' in df.columns:
                if 'last_name' not in df.columns:
                    tried_last_names = []
                    for key in last_name_list:
                        try:
                            df.rename(columns={key: 'last_name'}, inplace=True)
                            if 'last_name' not in df.columns:
                                tried_last_names.append(key)
                                if len(tried_last_names) == 3:
                                    try:
                                        df = df.rename(columns={df.filter(like='lastname').columns[0]: 'last_name'})
                                    except IndexError:
                                        # pass so can check if there is a 'name' column
                                        pass
                            else:
                                break
                        except:
                            raise IndexError("No columns match values in last_name_list")


        if 'first_name' and 'last_name' not in df.columns:
            if 'name' in df.columns:
                df[['first_name', 'last_name']] = df.name.str.split(' ', 1, expand=True)
            else:
                raise IndexError("No column names match first_name and last_name")


        email_list = [
            'email_address',
            'emailaddress',
            'email_(personal)_#1',
            'email_address_1',
            'email_1',
            'lead_email',
            'emails',
            ]

        if 'email' not in df.columns:
            tried_emails = []
            for key in email_list:
                try:
                    df.rename(columns={key: 'email'}, inplace=True)
                    if 'email' not in df.columns:
                        tried_emails.append(key)
                        if len(tried_emails) == 7:
                            try:
                                df = df.rename(columns={df.filter(like='email').columns[0]: 'email'})
                            except IndexError:
                                raise IndexError
                    else:
                        break
                except:
                    raise IndexError("No columns match values in email_list")


        phone_list = [
            'mobile_phone',
            'cell_phone',
            'primary_mobile_phone',
            'phone_(mobile)_#1',
            'telephone1',
            'phone_1',
            'phone_number',
            'lead_phone',
            'home_phone',
            'home_#',
            'phone_numbers',
            'phones',
            ]

        if 'phone' not in df.columns:
            tried_phones = []
            for key in phone_list:
                try:
                    df.rename(columns={key: 'phone'}, inplace=True)
                    if 'phone' not in df.columns:
                        tried_phones.append(key)
                        if len(tried_phones) == 12:
                            try:
                                df = df.rename(columns={df.filter(like='phone').columns[0]: 'phone'})
                            except IndexError:
                                raise IndexError
                    else:
                        break
                except:
                    raise IndexError("No columns match values in phone_list")


        """
        # this looks for a column like 'phone' with the least amount of code but can sometimes match homephone before mobile phone depending on CSV format
        # may switch to this if I don't think it will be an issue or current way grows seems too much
        if 'phone' not in df.columns:
            try:
                df = df.rename(columns={df.filter(like='phone').columns[0]: 'phone'})
            except IndexError:
                print('No columns including "phones" exists.')
        """


        # have to do this again to update cols variable with new column names in case some changed
        cols = list(df)

        # leaving these 2 just as a stafety check
        email_list = df['email']
        email_counts = email_list.value_counts()
        duplicate_emails = list(email_counts[email_counts > 1].index)
        print(f'Check these emails for duplicates: {duplicate_emails}')

        phone_list = df['phone']
        phone_list = phone_list.replace('[^0-9]+', '', regex=True)  # remove special characters
        phone_len = phone_list.str.len()
        phone_bad = list(phone_len[(phone_len < 8) | (phone_len > 15)].index)
        print(f'Check these lines for an incomplete phone number: {phone_bad}')


        # reorder columns to when they are merged it doesn't have double emails or phone numbers which bypasses the validation
        cols.insert(0, cols.pop(cols.index('first_name')))
        cols.insert(1, cols.pop(cols.index('last_name')))
        cols.insert(2, cols.pop(cols.index('email')))
        cols.insert(3, cols.pop(cols.index('phone')))
        df = df.reindex(columns=cols)


        if (df['email'].str.contains(',')).any():

            df['secondary_email'] = None
            df.columns = df.columns.fillna('secondary_email')

            # splits email list so that everything before comma is put in email and the rest into secondary_email
            df['email'], df['secondary_email'] = df['email'].str.split(',', 1).str

            if 'second_contact_email' in df.columns:  # this handles in case they do have the 'second_contact_email' column
                # Merges secondary_email into the 'second_contact_email' column
                df['second_contact_email'] = df['second_contact_email'].fillna('') + ', ' + df['secondary_email'].fillna('')
                # this is to just clean up column (i.e. remove leadning what space and random extra commas from merge)
                df['second_contact_email'] = df['second_contact_email'].replace('((, )$|[,]$)|(^\s)', '', regex=True)

                df = df.iloc[:, :-1]  # drops last column so there isn't double 'second_contact_email'

            df.rename(columns={'secondary_email': 'second_contact_email'}, inplace=True)
        else:
            pass

        # if there is a bad email then do stuff. its here to help with speed (not an issue but who knows) and to stop adding a second_contact_email when its not needed
        if ~df.email.str.contains(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$').all():
            if 'second_contact_email' in df.columns:
                # validate email and move bad ones
                df['temp_second_contact_email'] = df[~df['email'].str.contains(pat=r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', case=False, na=False)]['email']
                df['email'] = df[df['email'].str.contains(pat=r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', case=False, na=False)]['email']
                # merges columns so original second_contact_email doesn't get replaced by temp_second_contact_email
                df['second_contact_email'] = df['second_contact_email'].fillna('') + ', ' + df['temp_second_contact_email'].fillna('')
                del df['temp_second_contact_email']
                # this is to just clean up column (i.e. remove leadning what space and random extra commas from merge)
                df['second_contact_email'] = df['second_contact_email'].replace('((, )$|[,]$)|(^\s)', '', regex=True)
                # definitely not needed but one case bothered me so I added it
                df['second_contact_email'] = df['second_contact_email'].replace('(  )', ' ', regex=True)
            else:
                if 'second_contact_email' not in df.columns:
                    df['second_contact_email'] = ''
                    # validate email and move bad ones
                    df['temp_second_contact_email'] = df[~df['email'].str.contains(pat=r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', case=False, na=False)]['email']
                    df['email'] = df[df['email'].str.contains(pat=r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$', case=False, na=False)]['email']
                    # merges columns so original second_contact_email doesn't get replaced by temp_second_contact_email
                    df['second_contact_email'] = df['second_contact_email'].fillna('') + ', ' + df['temp_second_contact_email'].fillna('')
                    del df['temp_second_contact_email']
                    # this is to just clean up column (i.e. remove leadning what space and random extra commas from merge)
                    df['second_contact_email'] = df['second_contact_email'].replace('((, )$|[,]$)|(^\s)', '', regex=True)
                    # definitely not needed but one case bothered me so I added it
                    df['second_contact_email'] = df['second_contact_email'].replace('(  )', ' ', regex=True)


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


        if df.phone.str.contains(',').any():
            if 'second_contact_phone' in df.columns:
                # split phone numbers by comma and add to second_contact_phone
                df['phone'], df['temp_phone'] = df['phone'].str.split(',', 1).str
                df['second_contact_phone'] = df['second_contact_phone'].astype(str).fillna('') + ', ' + df['temp_phone'].astype(str).fillna('')
                del df['temp_phone']
            if 'second_contact_phone' not in df.columns:
                df['second_contact_phone'] = ''
                df['phone'], df['temp_phone'] = df['phone'].str.split(',', 1).str
                df['second_contact_phone'] = df['second_contact_phone'].astype(str).fillna('') + ', ' + df['temp_phone'].astype(str).fillna('')
                del df['temp_phone']

        # only keep numbers in phone column
        df['phone'] = df['phone'].replace('[^0-9]+', '', regex=True)

        # if there is a bad phone then do stuff. its here to help with speed (not an issue but who knows) and to stop adding a second_contact_phone when its not needed
        if df.phone.str.contains('^(?:(?!^.{,7}$|^.{16,}$).)*$').any():
            if 'second_contact_phone' in df.columns:
                # moves phone numbers less than 8 and greater than 15 digits then removes them from phone
                df['temp_second_contact_phone'] = df[~df['phone'].astype(str).str.contains(pat=r'^(?:(?!^.{,7}$|^.{16,}$).)*$', case=False, na=False)]['phone']
                df['phone'] = df[df['phone'].astype(str).str.contains(pat=r'^(?:(?!^.{,7}$|^.{16,}$).)*$', case=False, na=False)]['phone']
                # merges columns so original second_contact_email doesn't get replaced by temp_second_contact_email
                df['second_contact_phone'] = df['second_contact_phone'].astype(str).fillna('') + ', ' + df['temp_second_contact_phone'].astype(str).fillna('')
                del df['temp_second_contact_phone']
            else:
                if 'second_contact_phone' not in df.columns:
                    df['second_contact_phone'] = ''
                    # moves phone numbers less than 8 and greater than 15 digits then removes them from phone
                    df['temp_second_contact_phone'] = df[~df['phone'].astype(str).str.contains(pat=r'^(?:(?!^.{,7}$|^.{16,}$).)*$', case=False, na=False)]['phone']
                    df['phone'] = df[df['phone'].astype(str).str.contains(pat=r'^(?:(?!^.{,7}$|^.{16,}$).)*$', case=False, na=False)]['phone']
                    # merges columns so original second_contact_email doesn't get replaced by temp_second_contact_email
                    df['second_contact_phone'] = df['second_contact_phone'].astype(str).fillna('') + ', ' + df['temp_second_contact_phone'].astype(str).fillna('')
                    del df['temp_second_contact_phone']


        # gets rid of random nan that pops up sometimes
        df = df.replace('(?:^|\W)nan(?:$|\W)', '', regex=True)
        # these two just cleans up the file and gets rid of random commas. Not really necessary but you know makes the file less ugly
        df = df.replace('^(, )|^(,)', '', regex=True)
        df = df.replace('(, , )', ', ', regex=True)
        # this is to just clean up column (i.e. remove leadning what space, random extra commas from merge, and random .0)
        df['second_contact_phone'] = df['second_contact_phone'].replace('((, )$|[,]$|(^\s)|(\.0))', '', regex=True)
        # definitely not needed but one case bothered me so I added it
        df['second_contact_phone'] = df['second_contact_phone'].replace('(  )', ' ', regex=True)


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
