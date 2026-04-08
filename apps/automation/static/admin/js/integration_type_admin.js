/**
 * Dynamic form behavior for IntegrationTypeModel admin.
 * Shows/hides fields based on selected auth_type.
 * 
 * Requirements: 18.2
 */

(function($) {
    'use strict';
    
    $(document).ready(function() {
        const authTypeField = $('#id_auth_type');
        
        if (!authTypeField.length) {
            return;
        }
        
        // Field groups by auth type
        const fieldGroups = {
            oauth: [
                'oauth_client_id',
                'oauth_client_secret',
                'oauth_authorization_url',
                'oauth_token_url',
                'oauth_revoke_url',
                'oauth_scopes'
            ],
            meta: [
                'meta_app_id',
                'meta_app_secret',
                'meta_config_id',
                'meta_business_verification_url'
            ],
            api_key: [
                'api_key_endpoint',
                'api_key_header_name',
                'api_key_format_hint'
            ]
        };
        
        /**
         * Show/hide fields based on auth type
         */
        function updateFieldVisibility() {
            const selectedAuthType = authTypeField.val();
            
            // Hide all auth-specific fields first
            Object.values(fieldGroups).flat().forEach(function(fieldName) {
                const fieldRow = $('.field-' + fieldName);
                fieldRow.hide();
            });
            
            // Show fields for selected auth type
            const fieldsToShow = fieldGroups[selectedAuthType] || [];
            fieldsToShow.forEach(function(fieldName) {
                const fieldRow = $('.field-' + fieldName);
                fieldRow.show();
            });
            
            // Update fieldset visibility
            updateFieldsetVisibility(selectedAuthType);
        }
        
        /**
         * Update fieldset headers and descriptions
         */
        function updateFieldsetVisibility(authType) {
            // Hide all auth-specific fieldsets
            $('.field-oauth_client_id').closest('.module').hide();
            $('.field-meta_app_id').closest('.module').hide();
            $('.field-api_key_endpoint').closest('.module').hide();
            
            // Show the relevant fieldset
            if (authType === 'oauth') {
                $('.field-oauth_client_id').closest('.module').show();
            } else if (authType === 'meta') {
                $('.field-meta_app_id').closest('.module').show();
            } else if (authType === 'api_key') {
                $('.field-api_key_endpoint').closest('.module').show();
            }
        }
        
        /**
         * Add visual indicators for required fields
         */
        function updateRequiredFields() {
            const selectedAuthType = authTypeField.val();
            const fieldsToShow = fieldGroups[selectedAuthType] || [];
            
            fieldsToShow.forEach(function(fieldName) {
                const field = $('#id_' + fieldName);
                const label = $('label[for="id_' + fieldName + '"]');
                
                // Add asterisk for required fields (except optional ones)
                if (fieldName !== 'oauth_revoke_url' && 
                    fieldName !== 'api_key_format_hint' &&
                    !label.find('.required-indicator').length) {
                    label.append(' <span class="required-indicator" style="color: red;">*</span>');
                }
            });
        }
        
        /**
         * Add help text for HTTPS validation
         */
        function addHTTPSValidation() {
            const httpsFields = [
                'oauth_authorization_url',
                'oauth_token_url',
                'oauth_revoke_url'
            ];
            
            httpsFields.forEach(function(fieldName) {
                const field = $('#id_' + fieldName);
                if (field.length) {
                    field.on('blur', function() {
                        const value = $(this).val();
                        if (value && !value.startsWith('https://')) {
                            const helpText = $(this).siblings('.help');
                            if (helpText.length) {
                                helpText.css('color', 'red').text('⚠ OAuth URLs must use HTTPS protocol');
                            }
                        } else {
                            const helpText = $(this).siblings('.help');
                            if (helpText.length) {
                                helpText.css('color', '').text(helpText.data('original-text') || '');
                            }
                        }
                    });
                    
                    // Store original help text
                    const helpText = field.siblings('.help');
                    if (helpText.length) {
                        helpText.data('original-text', helpText.text());
                    }
                }
            });
        }
        
        // Initialize on page load
        updateFieldVisibility();
        updateRequiredFields();
        addHTTPSValidation();
        
        // Update when auth_type changes
        authTypeField.on('change', function() {
            updateFieldVisibility();
            updateRequiredFields();
        });
        
        // Add confirmation for auth type changes on existing objects
        if ($('input[name="_saveasnew"]').length === 0) {  // Not "Save as new"
            const originalAuthType = authTypeField.val();
            
            authTypeField.on('change', function() {
                const newAuthType = $(this).val();
                if (originalAuthType && newAuthType !== originalAuthType) {
                    const confirmed = confirm(
                        'Changing the authentication type will require reconfiguring all authentication settings. ' +
                        'Existing installations may need to be reinstalled. Continue?'
                    );
                    
                    if (!confirmed) {
                        $(this).val(originalAuthType);
                        updateFieldVisibility();
                    }
                }
            });
        }
    });
})(django.jQuery);
