function disable_enable_private_field() {
    var organization_visibility = jQuery('#organization_visibility').val();
    var workflow_status = jQuery('#workflow_status').val();
    var disabled = !(organization_visibility === 'all' && workflow_status === 'published');
    var private_field = jQuery('#field-private');
    if (disabled) {
        jQuery(private_field).val('True');
    }
    jQuery(private_field).prop('disabled', disabled);
}

  jQuery(document).ready(function() {
    jQuery('#workflow_status').on('change', function() {
        disable_enable_private_field();
    });

    jQuery('#organization_visibility').on('change', function() {
        disable_enable_private_field();
    });

    jQuery('.calendar input').datepicker({
        dateFormat: "yy-mm-dd"
    });

    jQuery('#field-license').on('change', function() {
        // Conditional changing field
    });

    // Insert required asterisk for organization label 
    jQuery('.control-label[for="field-organizations').prepend('<span title="This field is required" class="control-required">*</span> ')
  });