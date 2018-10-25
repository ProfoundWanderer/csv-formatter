from django.shortcuts import render
import logging
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.http import HttpResponse
import time
import pandas as pd
from cleancsv.header_list import rename_list, match_list


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
        if csv_file.multiple_chunks(chunk_size=5242880):
            messages.error(request, "Uploaded file is too big. Make sure file is less than 5 MB. (%.2f MB)." % (csv_file.size / (1000 * 1000),), extra_tags='alert')
            return HttpResponseRedirect(reverse("cleancsv:upload_csv"))

            """
            - Make rename/match thing a function?
            - Sometimes it adds .0 in columns (think solved by dtye=str) haven't been able to reproduce
            """

        start_time = time.time()
        # point to file location.
        # dtype=str so columns don't sometimes have .0 added and encoding to solve UnicodeDecodeError
        # removed sep=None (where pandas tries to get the delimiter) but raises sep=None so pandas tries to get the delimiter and 
        df = pd.read_csv(csv_file, sep=None, dtype=str, engine='python', encoding='ISO-8859-1')
        df.columns = [i.lower().replace(' ', '_') for i in df.columns]  # lower case and replace spaces
        df.index += 2  # so when it says "check these lines" the numbers match with csv
        # removes empty rows then empty columns
        df = df.dropna(how='all')
        df = df.dropna(axis=1, how='all')

        if 'first_name' and 'last_name' not in df.columns:
            if 'name' in df.columns:
                df[['first_name', 'last_name']] = df['name'].str.split(' ', 1, expand=True)
            # for top producer
            elif 'contact' in df.columns:
                df[['last_name', 'first_name']] = df['contact'].str.split(',', 1, expand=True)

        # might put into a functions
        # starts at -1 so it doesn't skip first entry in list
        i = -1
        # for each header column name in rename_list
        for rename_col in rename_list:
            i += 1
            # get  i  nested list in match_list (the list with all possible column names) and assign it to current_list
            current_list = match_list[i]
            # create empty list of tried column header list from current_list
            tried_colname = []
            # for each possible column name in current_list
            for try_col in current_list:
                # if the rename_col not in df 
                if rename_col not in df.columns:
                    try:
                        # try to find try_col in df and rename it to what rename_col is
                        df.rename(columns={try_col: rename_col}, inplace=True)
                        # add try_col to tried_col list so we don't try it again
                        tried_colname.append(try_col)
                        # if the rename does not add rename_col to df and i is less than 4 then do below
                        # I have i < 4 because the first 4 columns are needed to merger so they go through an additional matching attempt 
                        # and the others are just so the headers are automatically matched when uploaded
                        if rename_col not in df.columns and i < 4:
                            # if the number of items we tried equals the number of items in the list
                            if len(tried_colname) == len(current_list):
                                try:
                                    # try to find the first column in df that is similar to rename_col and rename it to rename_col
                                    df = df.rename(columns={df.filter(like=rename_col).columns[0]: rename_col})
                                    print('Filter match', rename_col)
                                    continue
                                # if try didn't work then throw exception since those 4 columns are needed for merger
                                except Exception as e:
                                    print(f"Unable to match a column the same as or close to {rename_col}. - Exception: {e}")
                                    break
                            else:
                                continue
                        # this breaks so it doesn't continue trying to check when it has already been match
                        elif rename_col in df.columns:
                            print(f"Matched {rename_col} with {try_col}.")
                            break
                        else:
                            print(f"Unable to match {rename_col} with {try_col}.")
                            continue
                    except Exception as e:
                        print(f"How did you get here!? - Exception: {e}")
                        break
                else:
                    break  # just to be safe


        # not needed since above raises an exception if any of the below columns aren't in df or matched this is just a safety check since it is quick
        if 'first_name' not in df.columns:
            raise KeyError('CSV file does not have a first_name column.')
        if 'last_name' not in df.columns:
            raise KeyError('CSV file does not have a last_name column.')
        if 'email' not in df.columns:
            raise KeyError('CSV file does not have a email column.')
        # phone may not be important for merger so testing
        # if 'phone' not in df.columns:
            # raise KeyError('CSV file does not have a phone column.')


        if 'address' not in df.columns:
            # if all of these things are columns in the df then combine them under the column name 'address'
            if set(['house_number', 'dir_prefix', 'street', 'street_type', 'dir_suffix', 'suite', 'po_box']).issubset(df.columns):
                df['address'] = (df['house_number'].astype(str).fillna('') + ' ' + df['dir_prefix'].astype(str).fillna('') + ' ' + 
                df['street'].astype(str).fillna('') + ' ' + df['street_type'].astype(str).fillna('') + ' ' + df['dir_suffix'].astype(str).fillna('') + ' ' + 
                df['suite'].astype(str).fillna('') + ' ' + df['po_box'].astype(str).fillna(''))
            elif set(['house_number', 'direction_prefix', 'street', 'street_designator', 'suite_no']).issubset(df.columns):
                df['address'] = (df['house_number'].astype(str).fillna('') + ' ' + df['direction_prefix'].astype(str).fillna('') + ' ' + 
                df['street'].astype(str).fillna('') + ' ' + df['street_designator'].astype(str).fillna('') + ' ' + df['suite_no'].astype(str).fillna(''))

        if 'assigned_agent' not in df.columns:
            # if these columns in the df then combine them under the column name 'assigned_agent'
            if set(['member_first_name', 'member_last_name']).issubset(df.columns):
                df['assigned_agent'] = df['member_first_name'].fillna('') + ' ' + df['member_last_name'].fillna('')

        if 'second_contact_name' not in df.columns:
            # if all of these things are columns in the df then combine them under the column name 'second_contact_name'
            if set(['secondary_title', 'secondary_first_name', 'secondary_nickname', 'secondary_last_name']).issubset(df.columns):
                df['second_contact_name'] = (df['secondary_title'].fillna('') + ' ' + df['secondary_first_name'].fillna('') + ' ' + 
                df['secondary_nickname'].fillna('') + df['secondary_last_name'].fillna(''))
            elif set(['first_name_2', 'last_name_2']).issubset(df.columns):
                df['second_contact_name'] = df['first_name_2'].fillna('') + ' ' + df['last_name_2'].fillna('')


        # assign list of df cols to 'cols' for when we move columns and merge rows
        cols = list(df)

        """
        email_list = df['email']
        email_counts = email_list.value_counts()
        duplicate_emails = list(email_counts[email_counts > 1].index)
        print(f'Check these emails for duplicates: {duplicate_emails}')

        phone_list = df['phone']
        phone_list = phone_list.replace('[^0-9]+', '', regex=True)  # remove special characters
        phone_len = phone_list.str.len()
        phone_bad = list(phone_len[(phone_len < 8) | (phone_len > 15)].index)
        print(f'Check these lines for an incomplete phone number: {phone_bad}')
        """

        # reorder columns to when they are merged it doesn't have double emails or phone numbers which bypasses the validation
        cols.insert(0, cols.pop(cols.index('first_name')))
        cols.insert(1, cols.pop(cols.index('last_name')))
        cols.insert(2, cols.pop(cols.index('email')))
        if 'phone' in df.columns:
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
        if ~df.email.str.contains(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-]+$').all():
            if 'second_contact_email' in df.columns:
                # validate email and move bad ones
                df['temp_second_contact_email'] = df[~df['email'].str.contains(pat=r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-]+$', case=False, na=False)]['email']
                df['email'] = df[df['email'].str.contains(pat=r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-]+$', case=False, na=False)]['email']
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
                    df['temp_second_contact_email'] = df[~df['email'].str.contains(pat=r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-]+$', case=False, na=False)]['email']
                    df['email'] = df[df['email'].str.contains(pat=r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-]+$', case=False, na=False)]['email']
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

        if 'phone' in df.columns:
            if df.phone.astype(str).str.contains(',').any():
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
            if df.phone.astype(str).str.contains('^(?:(?!^.{,7}$|^.{16,}$).)*$').any():
                if 'second_contact_phone' in df.columns:
                    # moves phone numbers less than 8 and greater than 15 digits then removes them from phone
                    df['temp_second_contact_phone'] = df[~df['phone'].astype(str).str.contains(pat=r'^(?:(?!^.{,7}$|^.{16,}$).)*$', case=False, na=False)]['phone']
                    df['phone'] = df[df['phone'].astype(str).str.contains(pat=r'^(?:(?!^.{,7}$|^.{16,}$).)*$', case=False, na=False)]['phone']
                    # merges columns so original second_contact_email doesn't get replaced by temp_second_contact_email
                    df['second_contact_phone'] = df['second_contact_phone'].astype(str).fillna('') + ', ' + df['temp_second_contact_phone'].astype(str).fillna('')
                    del df['temp_second_contact_phone']
                    # this is to just clean up column (i.e. remove leadning what space, random extra commas from merge, and random .0)
                    df['second_contact_phone'] = df['second_contact_phone'].replace('((, )$|[,]$|(^\s)|(\.0))', '', regex=True)
                    # definitely not needed but one case bothered me so I added it
                    df['second_contact_phone'] = df['second_contact_phone'].replace('(  )', ' ', regex=True)
                else:
                    if 'second_contact_phone' not in df.columns:
                        df['second_contact_phone'] = ''
                        # moves phone numbers less than 8 and greater than 15 digits then removes them from phone
                        df['temp_second_contact_phone'] = df[~df['phone'].astype(str).str.contains(pat=r'^(?:(?!^.{,7}$|^.{16,}$).)*$', case=False, na=False)]['phone']
                        df['phone'] = df[df['phone'].astype(str).str.contains(pat=r'^(?:(?!^.{,7}$|^.{16,}$).)*$', case=False, na=False)]['phone']
                        # merges columns so original second_contact_email doesn't get replaced by temp_second_contact_email
                        df['second_contact_phone'] = df['second_contact_phone'].astype(str).fillna('') + ', ' + df['temp_second_contact_phone'].astype(str).fillna('')
                        del df['temp_second_contact_phone']
                        # this is to just clean up column (i.e. remove leadning what space, random extra commas from merge, and random .0)
                        df['second_contact_phone'] = df['second_contact_phone'].replace('((, )$|[,]$|(^\s)|(\.0))', '', regex=True)
                        # definitely not needed but one case bothered me so I added it
                        df['second_contact_phone'] = df['second_contact_phone'].replace('(  )', ' ', regex=True)


        # gets rid of random nan that pops up sometimes
        df = df.replace('(?:^|\W)nan(?:$|\W)', '', regex=True)
        # these two just cleans up the file and gets rid of random commas. Not really necessary but you know makes the file less ugly
        df = df.replace('^(, )|^(,)', '', regex=True)
        df = df.replace('(, , )', ', ', regex=True)


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
