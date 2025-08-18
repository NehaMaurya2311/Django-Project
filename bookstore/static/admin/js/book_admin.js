// books/static/admin/js/book_admin.js - FIXED VERSION

(function($) {
    'use strict';
    
    $(document).ready(function() {
        console.log('Book admin JavaScript loaded.');
        
        const $categoryField = $('#id_category');
        const $subcategoryField = $('#id_subcategory'); 
        const $subsubcategoryField = $('#id_subsubcategory');
        
        // Only run if we are on a Book admin form page.
        if (!$categoryField.length) {
            console.log('Not on a book form page. Skipping dynamic load.');
            return;
        }

        // Helper function to update a select field's options
        function updateSelectOptions($field, options, helpText) {
            const currentValue = $field.val(); // Store current value
            
            $field.empty().append('<option value="">---------</option>');
            
            if (options && options.length > 0) {
                options.forEach(function(item) {
                    const $option = $('<option></option>')
                        .attr('value', item.id)
                        .text(item.name);
                    $field.append($option);
                });
                $field.prop('disabled', false);
                
                // Restore previous value if it exists in new options
                if (currentValue && options.some(opt => opt.id == currentValue)) {
                    $field.val(currentValue);
                }
            } else {
                $field.prop('disabled', true);
            }
            
            // Update help text if help element exists
            const $helpText = $field.siblings('.help-text, .help');
            if ($helpText.length) {
                $helpText.text(helpText || '');
            }
            
            console.log(`Updated ${$field.attr('id')} with ${options ? options.length : 0} options`);
        }

        // Function to load subcategories via AJAX
        function loadSubcategories(categoryId, skipTrigger = false) {
            if (!categoryId) {
                updateSelectOptions($subcategoryField, [], 'Select a category first');
                updateSelectOptions($subsubcategoryField, [], 'Select a subcategory first');
                return;
            }

            console.log('Fetching subcategories for category:', categoryId);

            // Show loading state
            $subcategoryField.empty()
                .append('<option value="">Loading subcategories...</option>')
                .prop('disabled', true);
            $subsubcategoryField.empty()
                .append('<option value="">---------</option>')
                .prop('disabled', true);

            $.ajax({
                url: '/books/ajax/load-subcategories/',
                method: 'GET',
                data: { 'category_id': categoryId },
                dataType: 'json',
                success: function(response) {
                    console.log('Subcategories response:', response);
                    
                    if (response.success !== false) {
                        updateSelectOptions(
                            $subcategoryField,
                            response.subcategories || [],
                            response.subcategories && response.subcategories.length > 0 
                                ? `Select a subcategory from ${response.category_name || 'this category'}` 
                                : 'No subcategories available for this category'
                        );
                        
                        // Trigger change event to load sub-subcategories if a value was selected
                        if (!skipTrigger && $subcategoryField.val()) {
                            $subcategoryField.trigger('change');
                        }
                    } else {
                        updateSelectOptions($subcategoryField, [], response.error || 'Error loading subcategories');
                    }
                },
                error: function(xhr, status, error) {
                    console.error('AJAX Error loading subcategories:', error);
                    updateSelectOptions($subcategoryField, [], 'Error loading subcategories. Please refresh the page.');
                }
            });
        }
        
        // Function to load sub-subcategories via AJAX
        function loadSubsubcategories(subcategoryId, skipTrigger = false) {
            if (!subcategoryId) {
                updateSelectOptions($subsubcategoryField, [], 'Select a subcategory first');
                return;
            }
            
            console.log('Fetching sub-subcategories for subcategory:', subcategoryId);
            
            // Show loading state
            $subsubcategoryField.empty()
                .append('<option value="">Loading sub-subcategories...</option>')
                .prop('disabled', true);

            $.ajax({
                url: '/books/ajax/load-subsubcategories/',
                method: 'GET',
                data: { 'subcategory_id': subcategoryId },
                dataType: 'json',
                success: function(response) {
                    console.log('Sub-subcategories response:', response);
                    
                    if (response.success !== false) {
                        updateSelectOptions(
                            $subsubcategoryField,
                            response.subsubcategories || [],
                            response.subsubcategories && response.subsubcategories.length > 0 
                                ? `Select a sub-subcategory from ${response.subcategory_name || 'this subcategory'}` 
                                : 'No sub-subcategories available for this subcategory'
                        );
                    } else {
                        updateSelectOptions($subsubcategoryField, [], response.error || 'Error loading sub-subcategories');
                    }
                },
                error: function(xhr, status, error) {
                    console.error('AJAX Error loading sub-subcategories:', error);
                    updateSelectOptions($subsubcategoryField, [], 'Error loading sub-subcategories. Please refresh the page.');
                }
            });
        }

        // Store initial values for edit forms
        const initialCategoryId = $categoryField.val();
        const initialSubcategoryId = $subcategoryField.val();
        const initialSubsubcategoryId = $subsubcategoryField.val();

        // Event listeners for user changes
        $categoryField.on('change', function() {
            const selectedCategoryId = $(this).val();
            console.log('Category changed to:', selectedCategoryId);
            
            // Clear dependent fields
            $subcategoryField.val('').prop('disabled', true);
            $subsubcategoryField.val('').prop('disabled', true);
            
            if (selectedCategoryId) {
                loadSubcategories(selectedCategoryId);
            } else {
                updateSelectOptions($subcategoryField, [], 'Select a category first');
                updateSelectOptions($subsubcategoryField, [], 'Select a subcategory first');
            }
        });

        $subcategoryField.on('change', function() {
            const selectedSubcategoryId = $(this).val();
            console.log('Subcategory changed to:', selectedSubcategoryId);
            
            // Clear dependent field
            $subsubcategoryField.val('').prop('disabled', true);
            
            if (selectedSubcategoryId) {
                loadSubsubcategories(selectedSubcategoryId);
            } else {
                updateSelectOptions($subsubcategoryField, [], 'Select a subcategory first');
            }
        });
        
        // Initial page load handling for edit forms
        if (initialCategoryId) {
            console.log('Initial category found:', initialCategoryId);
            
            // Load subcategories first
            loadSubcategories(initialCategoryId, true);
            
            // Wait a bit then restore subcategory value and load sub-subcategories
            setTimeout(function() {
                if (initialSubcategoryId) {
                    console.log('Restoring initial subcategory:', initialSubcategoryId);
                    $subcategoryField.val(initialSubcategoryId);
                    
                    // Load sub-subcategories
                    loadSubsubcategories(initialSubcategoryId, true);
                    
                    // Wait a bit more then restore sub-subcategory value
                    setTimeout(function() {
                        if (initialSubsubcategoryId) {
                            console.log('Restoring initial sub-subcategory:', initialSubsubcategoryId);
                            $subsubcategoryField.val(initialSubsubcategoryId);
                        }
                    }, 500);
                }
            }, 500);
        } else {
            // For new books, ensure fields are properly initialized
            updateSelectOptions($subcategoryField, [], 'Select a category first');
            updateSelectOptions($subsubcategoryField, [], 'Select a subcategory first');
        }

        // Debug: Add manual refresh buttons (remove after testing)
        if (window.location.search.includes('debug=1')) {
            $('<button type="button" class="btn btn-sm btn-info ms-2">Refresh Subcategories</button>')
                .insertAfter($categoryField)
                .on('click', function() {
                    loadSubcategories($categoryField.val());
                });
                
            $('<button type="button" class="btn btn-sm btn-info ms-2">Refresh Sub-subcategories</button>')
                .insertAfter($subcategoryField)
                .on('click', function() {
                    loadSubsubcategories($subcategoryField.val());
                });
        }
    });
})(django.jQuery || jQuery);