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


        start_time = time.time()
        """
        - Pandas read csv file and assigns it to df.
        - dtype=str so columns don't sometimes have .0 added and encoding to solve UnicodeDecodeError
        - Removed sep=None (where pandas tries to get the delimiter) but raises sep=None so pandas tries to get the delimiter
            if delimiters become an issue then I can try regex instead of None like I was trying to use before
        """
        df = pd.read_csv(csv_file, dtype=str, encoding='ISO-8859-1')
        df.columns = [i.lower().replace(' ', '_') for i in df.columns]  # lower case and replace spaces
        df.index += 2  # so when it says "check these lines" the numbers match with csv
        # removes empty rows then empty columns
        df = df.dropna(how='all')
        df = df.dropna(axis=1, how='all')

        if 'first_name' not in df.columns or 'last_name' not in df.columns:
            # for liondesk one off
            if 'name' in df.columns:
                if 'last_name' in df.columns:
                    df[['first_name', 'last_name']] = df['name'].str.split(' ', 1, expand=True)
                elif 'last_name' not in df.columns:
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
                                    continue
                                # if try didn't work then throw exception since those 4 columns are needed for merger
                                except Exception as e:
                                    break
                            else:
                                continue
                        # this breaks so it doesn't continue trying to check when it has already been match
                        elif rename_col in df.columns:
                            break
                        else:
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

        # moves values in first_name column that are more than 256 characters (that is the limit for the bulk import tool) to
        # the long_first_name column so it is not rejected
        if (df['first_name'].str.len() > 256).any():
            df['long_first_name'] = df[df['first_name'].str.len() > 256]['first_name']
            # only keeps values in the first_name column if it is less than or equal to 256 characters
            df['first_name'] = df[df['first_name'].str.len() <= 256]['first_name']
        if (df['last_name'].str.len() > 256).any():
            df['long_last_name'] = df[df['last_name'].str.len() > 256]['last_name']
            df['last_name'] = df[df['last_name'].str.len() <= 256]['last_name']

        # Got rid of astype(str) before .fillna('') and it resolved the random nan showing up in the address field
        if 'address' not in df.columns:
            # if all of these things are columns in the df then combine them under the column name 'address'
            if {'house_number', 'dir_prefix', 'street', 'street_type', 'dir_suffix', 'suite', 'po_box'}.issubset(
                    df.columns):
                df['address'] = (df['house_number'].fillna('') + ' ' + df['dir_prefix'].fillna('') + ' ' +
                                 df['street'].fillna('') + ' ' + df['street_type'].fillna('') + ' ' + df[
                                     'dir_suffix'].fillna('') + ' ' +
                                 df['suite'].fillna('') + ' ' + df['po_box'].fillna(''))
            elif {'house_number', 'direction_prefix', 'street', 'street_designator', 'suite_no'}.issubset(df.columns):
                df['address'] = (df['house_number'].fillna('') + ' ' + df['direction_prefix'].fillna('') + ' ' +
                                 df['street'].fillna('') + ' ' + df['street_designator'].fillna('') + ' ' + df[
                                     'suite_no'].fillna(''))

        if 'assigned_agent' not in df.columns:
            # if these columns in the df then combine them under the column name 'assigned_agent'
            if {'member_first_name', 'member_last_name'}.issubset(df.columns):
                df['assigned_agent'] = df['member_first_name'].fillna('') + ' ' + df['member_last_name'].fillna('')

        if 'second_contact_name' not in df.columns:
            # if all of these things are columns in the df then combine them under the column name 'second_contact_name'
            if {'secondary_title', 'secondary_first_name', 'secondary_nickname', 'secondary_last_name'}.issubset(
                    df.columns):
                df['second_contact_name'] = (
                            df['secondary_title'].fillna('') + ' ' + df['secondary_first_name'].fillna('') + ' ' +
                            df['secondary_nickname'].fillna('') + df['secondary_last_name'].fillna(''))
            elif {'first_name_2', 'last_name_2'}.issubset(df.columns):
                df['second_contact_name'] = df['first_name_2'].fillna('') + ' ' + df['last_name_2'].fillna('')

        # assign list of df cols to 'cols' for when we move columns and merge rows
        # not sure if needed now, need to go back and check
        cols = list(df)

        # reorder columns to when they are merged it doesn't have double emails or phone numbers which bypasses the validation
        cols.insert(0, cols.pop(cols.index('first_name')))
        cols.insert(1, cols.pop(cols.index('last_name')))
        cols.insert(2, cols.pop(cols.index('email')))
        if 'phone' in df.columns:
            cols.insert(3, cols.pop(cols.index('phone')))

        df = df.reindex(columns=cols)

        # makes contents of email column lower case so it doesn't think example@Yahoo.com and example@yahoo.com are different emails

        df['email'] = df.email.astype(str).str.lower()
        if (df['email'].str.contains(',')).any():

            df['secondary_email'] = None
            df.columns = df.columns.fillna('secondary_email')

            # splits email list so that everything before comma is put in email and the rest into secondary_email
            df['email'], df['secondary_email'] = df['email'].str.split(',', 1).str

            if 'second_contact_email' in df.columns:  # this handles in case they do have the 'second_contact_email' column
                # Merges secondary_email into the 'second_contact_email' column
                df['second_contact_email'] = df['second_contact_email'].fillna('') + ', ' + df[
                    'secondary_email'].fillna('')
                # this is to just clean up column (i.e. remove leadning what space and random extra commas from merge)
                df['second_contact_email'] = df['second_contact_email'].replace('((, )$|[,]$)|(^\s)', '', regex=True)

                df = df.iloc[:, :-1]  # drops last column so there isn't double 'second_contact_email'

            df.rename(columns={'secondary_email': 'second_contact_email'}, inplace=True)
        else:
            pass

        # if there is a bad email then do stuff. its here to help with speed (not an issue but who knows)
        # and to stop adding a second_contact_email when its not needed
        if ~df.email.str.contains(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-]+$').all():
            if 'second_contact_email' in df.columns:
                # validate email and move bad ones
                df['temp_second_contact_email'] = df[
                    ~df['email'].str.contains(pat=r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-]+$', case=False,
                                              na=False)]['email']
                df['email'] = df[
                    df['email'].str.contains(pat=r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-]+$', case=False,
                                             na=False)]['email']
                # merges columns so original second_contact_email doesn't get replaced by temp_second_contact_email
                df['second_contact_email'] = df['second_contact_email'].fillna('') + ', ' + df[
                    'temp_second_contact_email'].fillna('')
                del df['temp_second_contact_email']
                # this is to just clean up column (i.e. remove leadning what space and random extra commas from merge)
                df['second_contact_email'] = df['second_contact_email'].replace('((, )$|[,]$)|(^\s)', '', regex=True)
                # definitely not needed but one case bothered me so I added it
                df['second_contact_email'] = df['second_contact_email'].replace('(  )', ' ', regex=True)
            else:
                if 'second_contact_email' not in df.columns:
                    df['second_contact_email'] = ''
                    # validate email and move bad ones
                    df['temp_second_contact_email'] = df[
                        ~df['email'].str.contains(pat=r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-]+$', case=False,
                                                  na=False)]['email']
                    df['email'] = df[
                        df['email'].str.contains(pat=r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-]+$', case=False,
                                                 na=False)]['email']
                    # merges columns so original second_contact_email doesn't get replaced by temp_second_contact_email
                    df['second_contact_email'] = df['second_contact_email'].fillna('') + ', ' + df[
                        'temp_second_contact_email'].fillna('')
                    del df['temp_second_contact_email']
                    # this is to just clean up column (i.e. remove leadning what space and random extra commas from merge)
                    df['second_contact_email'] = df['second_contact_email'].replace('((, )$|[,]$)|(^\s)', '',
                                                                                    regex=True)
                    # definitely not needed but one case bothered me so I added it
                    df['second_contact_email'] = df['second_contact_email'].replace('(  )', ' ', regex=True)

        merge_on = ['email', 'contact_id']
        for merge in merge_on:
            if merge in df.columns:
                # filtering out columns 'first_name', 'last_name', 'email', 'contact_id' from df
                # so merger doesn't merge these columns, it just keeps the first instance of them
                new_df = df[df.columns.difference(['first_name', 'last_name', 'email', 'contact_id'])]

                # searches column named email and drops duplicates but keeps the first one and merges data
                df["first_dupe"] = df.duplicated(merge, keep=False) & ~df.duplicated(merge, keep="first")

                # https://github.com/khalido/notebooks/blob/master/pandas-dealing-with-dupes.ipynb
                # https://stackoverflow.com/questions/14940743/selecting-excluding-sets-of-columns-in-pandas
                def combine_rows(row, key=merge, cols_to_combine=new_df):
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
                                # so fields don't have multiple of the same thing because of the merge
                                # e.g. buyer,buyer because 2 merged rows have the type buyer, now it just puts buyer there once
                                if row[col] != dupe_row[col]:
                                    row[col] += ", " + dupe_row[col]
                                else:
                                    continue
                        # make sure first_dupe doesn't get processed again
                        row.first_dupe = False
                    return row

                df = df.apply(combine_rows, axis=1, result_type=None)
                # drops dup emails but keep first instance since everything should have been merged into that but ignores cells that are empty because
                # before it would just delete all rows with an empty email cell but the first one.....
                df = df[df[merge].isnull() | ~df[df[merge].notnull()].duplicated(subset=merge, keep='first')]
                df.groupby(merge).agg(lambda x: ", ".join(x)).reset_index()
                del df['first_dupe']

        if 'phone' in df.columns:
            if df.phone.astype(str).str.contains(',').any():
                if 'second_contact_phone' in df.columns:
                    # split phone numbers by comma and add to second_contact_phone
                    df['phone'], df['temp_phone'] = df['phone'].str.split(',', 1).str
                    df['second_contact_phone'] = df['second_contact_phone'].astype(str).fillna('') + ', ' + df[
                        'temp_phone'].astype(str).fillna('')
                    del df['temp_phone']
                if 'second_contact_phone' not in df.columns:
                    df['second_contact_phone'] = ''
                    df['phone'], df['temp_phone'] = df['phone'].str.split(',', 1).str
                    df['second_contact_phone'] = df['second_contact_phone'].astype(str).fillna('') + ', ' + df[
                        'temp_phone'].astype(str).fillna('')
                    del df['temp_phone']

            # only keep numbers in phone column
            df['phone'] = df['phone'].replace('[^0-9]+', '', regex=True)

            # if there is a bad phone then do stuff. its here to help with speed (not an issue but who knows) and to stop adding a second_contact_phone when its not needed
            if df.phone.astype(str).str.contains('^(?:(?!^.{,7}$|^.{16,}$).)*$').any():
                if 'second_contact_phone' in df.columns:
                    # moves phone numbers less than 8 and greater than 15 digits then removes them from phone
                    df['temp_second_contact_phone'] = df[
                        ~df['phone'].astype(str).str.contains(pat=r'^(?:(?!^.{,7}$|^.{16,}$).)*$', case=False,
                                                              na=False)]['phone']
                    df['phone'] = \
                    df[df['phone'].astype(str).str.contains(pat=r'^(?:(?!^.{,7}$|^.{16,}$).)*$', case=False, na=False)][
                        'phone']
                    # merges columns so original second_contact_email doesn't get replaced by temp_second_contact_email
                    df['second_contact_phone'] = df['second_contact_phone'].astype(str).fillna('') + ', ' + df[
                        'temp_second_contact_phone'].astype(str).fillna('')
                    del df['temp_second_contact_phone']
                    # this is to just clean up column (i.e. remove leadning what space, random extra commas from merge, and random .0)
                    df['second_contact_phone'] = df['second_contact_phone'].replace('((, )$|[,]$|(^\s)|(\.0))', '',
                                                                                    regex=True)
                    # definitely not needed but one case bothered me so I added it
                    df['second_contact_phone'] = df['second_contact_phone'].replace('(  )', ' ', regex=True)
                else:
                    if 'second_contact_phone' not in df.columns:
                        df['second_contact_phone'] = ''
                        # moves phone numbers less than 8 and greater than 15 digits then removes them from phone
                        df['temp_second_contact_phone'] = df[
                            ~df['phone'].astype(str).str.contains(pat=r'^(?:(?!^.{,7}$|^.{16,}$).)*$', case=False,
                                                                  na=False)]['phone']
                        df['phone'] = df[
                            df['phone'].astype(str).str.contains(pat=r'^(?:(?!^.{,7}$|^.{16,}$).)*$', case=False,
                                                                 na=False)]['phone']
                        # merges columns so original second_contact_email doesn't get replaced by temp_second_contact_email
                        df['second_contact_phone'] = df['second_contact_phone'].astype(str).fillna('') + ', ' + df[
                            'temp_second_contact_phone'].astype(str).fillna('')
                        del df['temp_second_contact_phone']
                        # this is to just clean up column (i.e. remove leadning what space, random extra commas from merge, and random .0)
                        df['second_contact_phone'] = df['second_contact_phone'].replace('((, )$|[,]$|(^\s)|(\.0))', '',
                                                                                        regex=True)
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
