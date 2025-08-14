// static/admin/js/book_admin.js
// JavaScript for handling dynamic dropdowns in Book admin form

(function($) {
    'use strict';

    $(document).ready(function() {
        var categoryField = $('#id_category');
        var subcategoryField = $('#id_subcategory');
        var subsubcategoryField = $('#id_subsubcategory');

        // Function to load subcategories
        function loadSubcategories(categoryId) {
            if (categoryId) {
                $.ajax({
                    url: '/books/ajax/load-subcategories/',
                    data: {
                        'category_id': categoryId
                    },
                    success: function (data) {
                        subcategoryField.empty();
                        subcategoryField.append('<option value="">---------</option>');
                        
                        if (data.subcategories && data.subcategories.length > 0) {
                            $.each(data.subcategories, function(index, subcategory) {
                                subcategoryField.append(
                                    '<option value="' + subcategory.id + '">' + 
                                    subcategory.name + '</option>'
                                );
                            });
                        }
                        
                        // Clear sub-subcategories
                        subsubcategoryField.empty();
                        subsubcategoryField.append('<option value="">---------</option>');
                    },
                    error: function() {
                        console.log('Error loading subcategories');
                    }
                });
            } else {
                subcategoryField.empty();
                subcategoryField.append('<option value="">---------</option>');
                subsubcategoryField.empty();
                subsubcategoryField.append('<option value="">---------</option>');
            }
        }

        // Function to load sub-subcategories
        function loadSubSubcategories(subcategoryId) {
            if (subcategoryId) {
                $.ajax({
                    url: '/books/ajax/load-subsubcategories/',
                    data: {
                        'subcategory_id': subcategoryId
                    },
                    success: function (data) {
                        subsubcategoryField.empty();
                        subsubcategoryField.append('<option value="">---------</option>');
                        
                        if (data.subsubcategories && data.subsubcategories.length > 0) {
                            $.each(data.subsubcategories, function(index, subsubcategory) {
                                subsubcategoryField.append(
                                    '<option value="' + subsubcategory.id + '">' + 
                                    subsubcategory.name + '</option>'
                                );
                            });
                        }
                    },
                    error: function() {
                        console.log('Error loading sub-subcategories');
                    }
                });
            } else {
                subsubcategoryField.empty();
                subsubcategoryField.append('<option value="">---------</option>');
            }
        }

        // Event handlers
        categoryField.change(function() {
            var categoryId = $(this).val();
            loadSubcategories(categoryId);
        });

        subcategoryField.change(function() {
            var subcategoryId = $(this).val();
            loadSubSubcategories(subcategoryId);
        });

        // Initialize on page load if editing existing book
        if (categoryField.val()) {
            var selectedSubcategory = subcategoryField.data('selected');
            var selectedSubSubcategory = subsubcategoryField.data('selected');
            
            loadSubcategories(categoryField.val());
            
            // Set selected subcategory after loading
            if (selectedSubcategory) {
                setTimeout(function() {
                    subcategoryField.val(selectedSubcategory);
                    loadSubSubcategories(selectedSubcategory);
                    
                    // Set selected sub-subcategory after loading
                    if (selectedSubSubcategory) {
                        setTimeout(function() {
                            subsubcategoryField.val(selectedSubSubcategory);
                        }, 500);
                    }
                }, 500);
            }
        }
    });
})(django.jQuery);