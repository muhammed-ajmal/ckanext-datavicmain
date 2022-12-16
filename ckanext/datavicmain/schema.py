RESOURCE_EXTRA_FIELDS = [
    # Last updated is a core field..
    # ('last_updated', {'label': 'Last Updated'}),
    ('filesize', {'label': 'Filesize'}),
    ('release_date', {'label': 'Release Date', 'field_type': 'date'}),
    ('period_start', {'label': 'Temporal Coverage Start', 'field_type': 'date'}),
    ('period_end', {'label': 'Temporal Coverage End', 'field_type': 'date'}),
    ('data_quality', {'label': 'Data Quality Statement', 'field_type': 'textarea'}),
    ('attribution', {'label': 'Attribution Statement', 'field_type': 'textarea'}),
]

# Format (tuple): ( 'field_id', { 'field_attribute': 'value' } )
DATASET_EXTRA_FIELDS = [
    #
    # SPECIFICALLY place fields
    #
    # ('last_modified_user_id',  {'label': 'Last Modified By'}),
    ('extract', {'label': 'Abstract', 'field_type': 'textarea', 'required': True}),
    ('primary_purpose_of_collection', {'label': 'Purpose', 'field_type': 'textarea'}),
    ('agency_program_domain', {'label': 'Agency Program/Domain'}),
    ('category', {'label': 'Category', 'required': True}),

    #
    # GENERAL field cluster
    #
    # License
    ('custom_licence_text', {'label': 'License - other', 'field_group': 'general'}),
    ('custom_licence_link', {'label': 'Custom license link', 'field_group': 'general'}),
    ('date_created_data_asset', {
        'label': 'Created (Data Asset)',
        'field_type': 'date',
        'field_group': 'general',
        'required': True
    }),
    # Published (Metadata Record) (CKAN date published to data dir)
    ('date_modified_data_asset', {'label': 'Last Modified (Data Asset)', 'field_type': 'date', 'field_group': 'general'}),
    ('update_frequency', {
        'label': 'Update Frequency',
        'field_type': 'select',
        'options': [
            {'value': '', 'text': 'Please select'},
            {'value': 'continual', 'text': 'Continual'},
            {'value': 'daily', 'text': 'Daily'},
            {'value': 'weekly', 'text': 'Weekly'},
            {'value': 'fortnightly', 'text': 'Fortnightly'},
            {'value': 'monthly', 'text': 'Monthly'},
            {'value': 'quarterly', 'text': 'Quarterly'},
            {'value': 'biannually', 'text': 'Biannually'},
            {'value': 'annually', 'text': 'Annually'},
            {'value': 'asNeeded', 'text': 'As Needed'},
            {'value': 'irregular', 'text': 'Irregular'},
            {'value': 'notPlanned', 'text': 'Not Planned'},
            {'value': 'unknown', 'text': 'Unknown'},
        ],
        'field_group': 'general',
        'required': True
    }),
    ('full_metadata_url', {'label': 'Full Metadata URL', 'field_group': 'general'}),

    #
    # SECURITY field cluster
    #
    # Personal Data (Privacy)
    ('personal_information', {
        'label': 'Personal Data (Privacy)',
        'description': '',
        'field_type': 'select',
        'options': [
            {'value': '', 'text': 'Please select'},
            {'value': 'not_yet', 'text': 'Not yet assessed'},
            {'value': 'yes', 'text': 'Yes'},
            {'value': 'yes_de_identified', 'text': 'Yes - with de-identified data'},
            {'value': 'no', 'text': 'No'},
        ],
        'field_group': 'security',
        'required': True
    }),
    ('protective_marking', {
        'label': 'Protective Marking', 'field_type': 'select',
        'options': [
            {'value': '',
             'text': 'Please select'},
            {'value': 'secret',
             'text': 'SECRET'},
            {'value': 'protected',
             'text': 'PROTECTED'},
            {'value': 'cabinet_in_confidence_secret',
             'text': 'Cabinet-in-confidence: SECRET'},
            {'value': 'cabinet_in_confidence_protected',
             'text': 'Cabinet-in-confidence: PROTECTED'},
            {'value': 'official_sensitive',
             'text': 'OFFICIAL: Sensitive'},
            {'value': 'official',
             'text': 'OFFICIAL'},
        ],
        'field_group': 'security',
        'required': True
    }),
    ('access', {
        'label': 'Access',
        'field_type': 'select',
        'options': [
            {'value': '', 'text': 'Please select'},
            {'value': 'yes', 'text': 'Yes'},
            {'value': 'no', 'text': 'No'},
            {'value': 'not_yet', 'text': 'Not yet assessed'},
        ],
        'field_group': 'security',
        'required': True
    }),
    ('access_description', {'label': 'Access - description', 'field_type': 'textarea', 'field_group': 'security'}),
    # Business Impact Level - Confidentiality Breach
    ('bil_confidentiality', {
        'label': 'Business Impact Level - Confidentiality Breach',
        'field_type': 'select',
        'options': [
            {'value': '', 'text': 'Please select'},
            {'value': 'n_a', 'text': 'N/A'},
            {'value': 'minor', 'text': 'Minor'},
            {'value': 'limited', 'text': 'Limited'},
            {'value': 'major', 'text': 'Major'},
            {'value': 'serious', 'text': 'Serious'},
            {'value': 'exceptional', 'text': 'Exceptional'},
        ],
        'field_group': 'security'
    }),
    # Business Impact Level - Confidentiality Breach Description
    ('bil_confidentiality_description', {
        'label': 'Business Impact Level - Confidentiality Breach description',
        'field_type': 'textarea',
        'field_group': 'security'
    }),
    # Business Impact Level - Availability
    ('bil_availability', {
        'label': 'Business Impact Level - Availability',
        'field_type': 'select',
        'options': [
            {'value': '', 'text': 'Please select'},
            {'value': 'n_a', 'text': 'N/A'},
            {'value': 'minor', 'text': 'Minor'},
            {'value': 'limited', 'text': 'Limited'},
            {'value': 'major', 'text': 'Major'},
            {'value': 'serious', 'text': 'Serious'},
            {'value': 'exceptional', 'text': 'Exceptional'},
        ],
        'field_group': 'security'
    }),
    # Business Impact Level - Availability description
    ('bil_availability_description', {
        'label': 'Business Impact Level - Availability description',
        'field_type': 'textarea',
        'field_group': 'security'
    }),
    # Business Impact Level - Integrity
    ('bil_integrity', {
        'label': 'Business Impact Level - Integrity',
        'field_type': 'select',
        'options': [
            {'value': '', 'text': 'Please select'},
            {'value': 'n_a', 'text': 'N/A'},
            {'value': 'minor', 'text': 'Minor'},
            {'value': 'limited', 'text': 'Limited'},
            {'value': 'major', 'text': 'Major'},
            {'value': 'serious', 'text': 'Serious'},
            {'value': 'exceptional', 'text': 'Exceptional'},
        ],
        'field_group': 'security'
    }),
    # Business Impact Level - Integrity description
    ('bil_integrity_description', {
        'label': 'Business Impact Level - Integrity description',
        'field_type': 'textarea',
        'field_group': 'security'
    }),
    # Source ICT System/Container
    ('source_ict_system', {'label': 'Source ICT System', 'field_group': 'security'}),

    ('record_disposal_category', {'label': 'Record Disposal Category', 'field_group': 'security'}),
    ('disposal_category', {'label': 'Disposal Category', 'field_group': 'security'}),
    ('disposal_class', {'label': 'Disposal Class', 'field_group': 'security'}),

    #
    # WORKFLOW field cluster
    #
    # NOTE: the use of the Z in organization for consistency with usage throughout CKAN
    ('organization_visibility', {'label': 'Organisation Visibility', 'field_group': 'workflow_1'}),
    # Public Release is managed using the core CKAN Private field (true/false - private/public)
    ('workflow_status', {'label': 'Workflow Status', 'field_group': 'workflow_2'}),
    ('workflow_status_notes', {'label': 'Workflow Status Notes', 'field_type': 'textarea', 'field_group': 'workflow_2'}),

    #
    # CUSTODIAN field cluster
    #
    # Data Owner - agency_program
    ('data_owner', {'label': 'Data Owner', 'field_group': 'custodian'}),
    # Data Custodian
    # Role
    ('role', {'label': 'Role', 'field_group': 'custodian'}),
    # Email
    # Uses CKAN core field `maintainer_email`
]


def get_options(option_list):
    options = []
    if option_list is not None:
        for option in option_list:
            options.append(option.get('value'))
    return options


def get_option_label(type, field, value):
    if type == 'dataset':
        schema = DATASET_EXTRA_FIELDS
    else:
        schema = RESOURCE_EXTRA_FIELDS

    for element in schema:
        if element[0] == field:
            schema_field = element
            break

    if schema_field and 'options' in schema_field[1]:
        for option in schema_field[1]['options']:
            if option['value'] == value:
                value = option['text']
                break
    return value
