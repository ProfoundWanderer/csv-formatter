rename_list = [
    'first_name',
    'last_name',
    'email',
    'phone',
    'type',
    'assigned_agent',
    'assigned_lender',
    'alternate_phone',
    'street_address',
    'city',
    'state',
    'zip',
    'fax',
    'office_phone',
    'second_contact_phone',
    'status',
    'timeframe',
    'area',
    'home_type',
    'source_details',
    'minimum_bedrooms',
    'minimum_bathrooms',
    'minimum_price',
    'maximum_price',
    'start_date',
    'last_active_at',
    'last_communication_at',
    'average_property_price',
]

match_list = [
    [  # first_name
        'firstname',
        'primary_firstname',
        'lead_first_name',
        'name_first',
        'first-name',
        'name_first',
    ], [  # last_name
        'lastname',
        'primary_lastname',
        'lead_last_name',
        'name_last',
        'last-name',
        'name_last',
    ], [  # email
        'email_address',
        'emailaddress',
        'email_(personal)_#1',
        'email_address_1',
        'email_1',
        'email1',
        'primary_email',
        'lead_email',
        'e-mail_address',
        'subscriber_email',
        'e-mail_1_-_value',
        'emails',
    ], [  # phone
        'mobile_phone',
        'cell_phone',
        'primary_mobile_phone',
        'phone_(mobile)_#1',
        'telephone1',
        'phone_1',
        'phone_number',
        'telephone_mobile',
        'phone(where_available)',
        'lead_phone',
        'cell_phone_#',
        'phone_#',
        'phone_(mobile)',
        'phone-mobile',
        'phone-primary',
        'phone_1_-_value',
        'phone_mobile',
        'phone_landline',
        'home_phone',
        'home_#',
        'work_phone',
        'phone_numbers',
        'phones',
    ], [  # type
        'contact_type',
        'leadtype',
        'buyer/seller',
        'buyer_seller',
    ], [  # assigned_agent
        'agent',
        'agentname',
        'lead_assigned_to_name',
        'realtor',
        'agent_assigned',
        'buyeragent',
        'assigned_staff',
        'lead_owner',
        'agent_id',
        'assigned_to',
        'owner',
    ], [  # assigned_lender
        'lender',
    ], [  # alternate_phone
        'home_phone',
        'phone_2',
    ], [  # street_address
        'address',
        'address1',
        'address_1',
        'street_1',
        'address_street_1',
        'home_street',
        'address_1_-_street',
        'address-home-street1',
    ], [  # city
        'address_city',
        'city_1',
        'home_city',
        'address_1_-_city',
        'address-home-city',
    ], [  # state
        'state_1',
        'address_state',
        'home_state',
        'address_1_-_state',
        'address-home-state',
        'province',
    ], [  # zip
        'zipcode',
        'zip_1',
        'address_zip',
        'home_postal_code',
        'address_1_-_zip',
        'address-home-zip',
        'postal_code',
    ], [  # fax
        'fax_number',
        'business_fax',
        'home_fax',
    ], [  # office_phone
        'work_phone',
        'business_phone',
        'bus_phone',
    ], [  # second_contact_phone
        'secondary_contact_phone',
    ], [  # status
        'statusname',
        'pipeline_status',
    ], [  # timeframe
        'timeframe',
        'timeframetype',
        'buying_timeframe',
    ], [  # area
        'looking_in',
        'areasearchedmost',
        'location',
        'favorite_city',
    ], [  # home_type
        'averagepropertytypeviewed',
        'property_type',
    ], [  # source_details
        'source',
        'lead_source',
        'originalsource',
        'source_page_name',
        'sub_source',
        'website_source',
    ], [  # minimum_bedrooms
        'averagebedsviewed',
        'bedrooms',
    ], [  # minimum_bathrooms
        'averagebathsviewed',
        'bathrooms',
    ], [  # minimum_price
        'min_price_preference',
    ], [  # maximum_price
        'max_price_preference',
    ], [  # start_date
        'datecreated',
        'register_date',
        'registered',
        'date_added',
        'registerdate',
        'contact_created_date',
        'registration_date',
        'creation_date',
        'created_at',
    ], [  # last_active_at
        'dateactivity',
        'last_login',
        'lastvisitdate',
    ], [  # last_communication_at
        'lastphonecall',
        'last_contacted_at',
    ], [  # average_property_price
        'average_price',
        'averageprice',
        'list_price',
        'avglistingprice',
    ]
]
