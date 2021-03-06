(

    // TODO: there may be a problem here with various element ids. These widgets may produce/rely on
    //       duplicate id's in the dom.
    function($) {

        // helper function for selectable behaviour
        function selectable($elements) {
            $elements.click(function(event) {
                // get parent row div
                var $row = $(event.target).closest('div.row');
                // get input element (radio / checkbox)
                var $input = $row.find('input');
                // new state for input element
                if (! $input.is(event.target)) {
                    // if click was on input element checked state
                    // has already been set
                    var setchecked = ! $input.prop('checked');
                    // apply new state
                    $input.prop('checked', setchecked);
                };
                // update row class according to new checked state
                $row.parent().find('div.row:has(input:checked)').addClass("ui-selected");
                $row.parent().find('div.row:has(input:not(:checked))').removeClass("ui-selected");
            });
        };

        // An object to handle Modal dialog for the widgets defined here
        function ModalBrowseSelect($modal, options) {
            // $modal ... the jquery object for the modal element on the page
            var settings = $.extend({
                remote: 'datasets_listing_popup', //
                pagination_selector: 'div.listingBar a',
                result_child_selector: '#datasets-popup-result-list',
                multiple: undefined,
                initial_filters: undefined,
                filters: undefined
            }, options);
            
            // make sure the modal dialog is a top level element on the page
            $modal.prependTo($('body'));

            // init modal events
            $modal.on('hidden', _clear);

            // apply button clicked
            $modal.find('button.btn-primary').click(function(event) {
                event.preventDefault();
                // trigger new event
                $modal.trigger('modalapply');
            });

            function show() {
                // first gather all request parameters we need
                var params = [{
                    name: 'datasets.multiple',
                    value: settings.multiple
                }];
                // filters to show in dialog
                $.each(settings.filters, function(index, value) {
                    params.push({name: 'datasets.filters:list',
                                 value: value});
                });
                // add hidden query parameters
                for (var key in settings.initial_filters) {
                    // only consdier own propertys
                    if (settings.initial_filters.hasOwnProperty(key)) {
                        // iterate over values
                        if (!settings.initial_filters[key]) {
                            // ignore filters without value
                            continue;
                        }
                        $.each(settings.initial_filters[key], function(index, value) {
                            params.push({
                                name: 'datasets.filter.' + key,
                                value: value
                            });
                        });
                    }
                };
                // show dialog
                // bootstrap 2 modal does'n have loaded event so we have to do it ourselves
                $modal.modal('show');
                _load_search_results(settings.remote + '?' + $.param(params));
            };

            function close() {
                $modal.modal('hide');
            };

            // hide and clear modal
            function _clear() {
                $(this).removeData('modal');
                $(this).find('.modal-body').empty();
            };

            function _load_search_results(url) {
                $modal.find('.modal-body').load(url, _bind_events_on_modal_content);
            };
            
            // initialise modal when finished loading
            function _bind_events_on_modal_content() {
                // hookup events within modal
                $modal.find('form').submit(function(event) {
                    event.preventDefault();
                    _load_search_results($(this).attr('action') + '?' +  $(this).serialize());
                });
                // apply selectable behaviour to result list
                selectable($modal.find(settings.result_child_selector));
                // intercept pagination links
                $modal.find(settings.pagination_selector).click( function(event) {
                    event.preventDefault();
                    // no params needed as they are already set up on the pagination link
                    _load_search_results($(this).attr('href'));
                });
            };

            function get_selected() {
                return $modal.find('.ui-selected');
            };

            function set_initial_filters(initial_filters) {
                settings.initial_filters = initial_filters;
            };

            function get_initial_filters() {
                return settings.initial_filters;
            };

            return {
                $element: $modal,
                show: show,
                close: close,
                get_selected: get_selected,
                set_initial_filters: set_initial_filters,
                get_initial_filters: get_initial_filters
            }
                    
        };

        // single select widget
        // TODO: multi not implemented here?        
        function select_dataset($element, options) {

            // required options: field, genre
            var settings = $.extend({
                // These are the defaults.
                widgetid: 'form-widget-' + options.field, // id of widget main top element
                widgetname: 'form.widgets.' + options.field, // name of the input field
                widgeturl: location.origin + location.pathname + '/++widget++' + options.field, // used to reload entire widget
                // modal settings
                target: '#' + options.field + '-modal',
                remote: 'datasets_listing_popup', // modal box id                
                filters: ['text', 'source'],
                multiple: undefined,
                experimenttype: undefined
            }, options );

            // modal dialog
            var modal = new ModalBrowseSelect(
                $(settings.target),
                {
                    remote: settings.remote,
                    multiple: settings.multiple,
                    filters: settings.filters,
                    initial_filters: {
                        'genre:list': settings.genre,
                        'experimenttype:list': settings.experimenttype
                    }
                }
            );

            // hookup popup button/link to show modal
            $element.click(function(event) {
                event.preventDefault();
                // show modal
                modal.show();
            });

            // when user preses 'save' button in modal
            modal.$element.on('modalapply', function(event) {
                var $widgetroot = $('#' + settings.widgetid);
                // get selected element
                var $selected = modal.get_selected();
                // we have all the data we need so get rid of the modal
                modal.close();
                if ($selected.length) {
                    var params = [];
                    if (settings.multiple) {
                        // if multiple fetch current selection
                        params = $widgetroot.find('input,select').serializeArray();
                    }
                    $.each($selected, function(index, value){
                        params.push({name: settings.widgetname + ':list',
                                     value: $(value).attr('data-uuid')});
                    });
                    reload_widget(params);
                }
            });

            // allow user to remove selected elements
            $('#' + settings.widgetid).on('click', 'a:has(i.icon-remove)',
                function(event) {
                    event.preventDefault();
                    $(this).parents('div.selecteditem').remove();
                    // trigger change event on widget update
                    $(event.delegateTarget).trigger('widgetChanged');
                    // TODO: shall we reload the widget?
                }
            );
            
            // reload widget via ajax
            function reload_widget(params) {
                var $widgetroot = $('#' + settings.widgetid);
                $widgetroot.load(
                    settings.widgeturl + ' #' + settings.widgetid + ' >',
                    params,
                    function(text, status, xhr) {
                        // trigger change event on widget update                        
                        $(this).trigger('widgetChanged');
                    }
                );
            };

        };

        // multi layer select widget
        function select_dataset_dict($element, options) {

            // required options: field, genre

            var settings = $.extend({
                // These are the defaults.
                widgetid: 'form-widgets-' + options.field, // id of widget main top element
                widgetname: 'form.widgets.' + options.field, // name of the input field
                widgeturl: location.origin + location.pathname + '/++widget++' + options.field,
                // modal settings
                target: '#' + options.field + '-modal',
                remote: 'datasets_listing_popup',
                filters: ['text', 'source', 'layer', 'resolution'],
                multiple: 'multiple',
                experimenttype: undefined,
            }, options );

            // modal dialog
            var modal = new ModalBrowseSelect(
                $(settings.target),
                {
                    remote: settings.remote,
                    multiple: settings.multiple,
                    filters: settings.filters,
                    initial_filters: {
                        'genre:list': settings.genre,
                        'experimenttype:list': settings.experimenttype
                    }
                }
            );

            // hookup popup button/link to show modal
            $element.click(function(event) {
                event.preventDefault();
                // show modal
                modal.show();
            });
            
            // when user preses 'save' button in modal
            modal.$element.on('modalapply', function(event) {
                var $widgetroot = $('#' + settings.widgetid);                
                // get selected element
                var $selected = modal.get_selected();
                // we have all the data we need so get rid of the modal
                modal.close();
                if ($selected.length) {
                    // first update .count field on widget
                    var $count = $('input[name="' + settings.widgetname + '.count"]');
                    var count = parseInt($count.val()) || 0;
                    $count.val(count + $selected.length);
                    // get current params from widget
                    var params = $widgetroot.find('input,select').serializeArray();
                    // collect newly selected layers
                    $.each($selected, function(index, value){
                        params.push({name: settings.widgetname + '.item.' + count,
                                     value: $(value).attr('data-uuid')});
                        count += 1;
                    });
                    // add count parameter if it was not on page already
                    if ($count.length == 0) {
                        params.push({name: settings.widgetname + '.count',
                                     value: count});
                    }
                    // fetch html for widget
                    reload_widget(params);
                }
            });

            // allow user to remove selected elements
            $('#' + settings.widgetid).on('click', 'a:has(i.icon-remove)',
                function(event) {                                                        
                    event.preventDefault();
                    $(this).parents('div.selecteditem').remove();
                    // trigger change event on widget update
                    $(event.delegateTarget).trigger('widgetChanged');
                }
            );

            // reload widget via ajax
            function reload_widget(params) {
                var $widgetroot = $('#' + settings.widgetid);
                $widgetroot.load(
                    settings.widgeturl + ' #' + settings.widgetid + ' >',
                    params,
                    function(text, status, xhr) {
                        // trigger change event on widget update
                        $(this).trigger('widgetChanged');
                    }
                );
            };
            
        };


        // TODO: below is a modified copy of bccvl.select_dataset, ideally these sholud be merged into one
        //       -> needs better ajax param processing. (maybe via hidden input fields?)

        // single/multi select dataset widget
        function select_dataset_future($element, options) {

            // TODO: on init fetch settings.params from other widget

            // required options: field, genre
            var settings = $.extend({
                // These are the defaults.
                widgetid: 'form-widget-' + options.field, // id of widget main top element
                widgetname: 'form.widgets.' + options.field, // name of the input field
                widgeturl: location.origin + location.pathname + '/++widget++' + options.field, // used to reload entire widget
                // modal settings
                target: '#' + options.field + '-modal',
                remote: 'datasets_listing_popup', // modal box id
                filters: ['text', 'source', 'resolution', 'emsc', 'gcm'],
                multiple: 'multiple',
                experimenttype: undefined
            }, options );

            // modal dialog
            var modal = new ModalBrowseSelect(
                $(settings.target),
                {
                    remote: settings.remote,
                    multiple: settings.multiple,
                    filters: settings.filters,
                    initial_filters: {
                        'genre:list': settings.genre,
                        'experimenttype:list': settings.experimenttype
                        // following parameters will be added dynamically... their values depend
                        // on the selection within another widget
                        //'resolution:list': settings.params.resolution,
                        //'layer:list': settings.params.layers
                    }
                }
            );
            
            // hookup popup button/link to show modal
            $element.click(function(event) {
                event.preventDefault();
                // show modal
                modal.show();
            });
            
            // when user preses 'save' button in modal
            modal.$element.on('modalapply', function(event) {
                var $widgetroot = $('#' + settings.widgetid);
                // get selected element
                var $selected = modal.get_selected();
                // we have all the data we need so get rid of the modal
                modal.close();
                if ($selected.length) {
                    // get current params for widget
                    var params = $widgetroot.find('input,select').serializeArray();                    
                    // TODO: this different to original ... maybe adding to current can depend on settings.multiple?
                    // add newly selected datasets
                    $.each($selected, function(index, value){
                        params.push({name: settings.widgetname + ':list',
                                     value: $(value).attr('data-uuid')});
                    });
                    reload_widget(params);
                }
            });

            $('#' + settings.widgetid).on('click', 'a:has(i.icon-remove)',
                function(event) {
                    event.preventDefault();
                    $(this).parents('div.selecteditem').remove();
                    // trigger change event on widget update
                    $(event.delegateTarget).trigger('widgetChanged');
            });

            function reload_widget(params) {
                var $widgetroot = $('#' + settings.widgetid);
                $widgetroot.load(
                    settings.widgeturl + ' #' + settings.widgetid + ' >',
                    params,
                    function(text, status, xhr) {
                        // trigger change event when widget has been updated
                        $(this).trigger('widgetChanged');
                    }
                );
            };

            
            // TODO: this is different to original
            //       there is also a hardcoded reference to another widget this one depends on
            $('#form-widgets-species_distribution_models-selected')
                .on('widgetChanged', function(event, par1, par2) {
                    // update settings with new search parameters
                    var $exp = $(this).find('p.experiment-title');
                    var newparams;
                    if ($exp.length > 0) {
                        newparams = {
                            'layers:list': $exp.data('layers').split(','),
                            'resolution:list': [$exp.data('resolution')]
                        };
                    }
                    // check if params have changed
                    var oldparams = modal.get_initial_filters();
                    if ((oldparams.layers === undefined || oldparams.resolution == undefined ||
                        newparams === undefined || newparams === null) ||
                        oldparams.layers.sort().join() != newparams.layers.sort().join() ||
                        oldparams.resolution != newparams.resolution) {
                        // there are either no new settings or new settings are different
                        //let's update this widget here
                        // TODO: shall we reload the widget here? to make sure we have all empty input markers?
                        $('#' + settings.widgetid).empty(); // clear widget
                        if (newparams === undefined || newparams === null) {
                            // reset initial filters
                            modal.set_initial_filters({
                                'genre:list': settings.genre,
                                'experiment:list': settings.experimenttype
                            });
                        } else {
                            // set new initial filters
                            // we have a reference to the internal object so we can just update it
                            $.extend(oldparams, newparams);
                        }
                    }

                });
        };


        // single/multi select dataset widget
        // TODO: again a copy of bccvl.select_dataset
        function select_experiment($element, options) {

            // required options: field, genre

            var settings = $.extend({
                // These are the defaults.
                widgetid: 'form-widget-' + options.field, // id of widget main top element
                widgetname: 'form.widgets.' + options.field, // name of the input field
                widgeturl: location.origin + location.pathname + '/++widget++' + options.field, // used to reload entire widget
                // modal settings
                target: '#' + options.field + '-modal',
                remote: 'datasets_listing_popup', // modal box id
                filters: ['text', 'source'],
                experimenttype: undefined
            }, options );

            // TODO: this is different to original
            //       there is also a hardcoded reference to another widget this one depends on
            // init settings experimenttype from widget if necessary
            var $experiment_type = $('#form-widgets-experiment_type');
            if (!settings.experimenttype && $experiment_type.val()) {
                settings.experimenttype = [$experiment_type.val()];
            }
            // init selectize boxes on page load
            $.each($('#' + settings.widgetid).find('select'), function(index, elem) {
                $(elem).selectize({create: true,
                                   persist: false});
            });
            
            // end diff

            // modal dialog
            var modal = new ModalBrowseSelect(
                $(settings.target),
                {
                    remote: settings.remote,
                    multiple: settings.multiple,
                    filters: settings.filters,
                    initial_filters: {
                        'genre:list': settings.genre,
                        // TODO: dynamic?
                        'experimenttype:list': settings.experimenttype
                    }
                }
            );
            
            // hookup popup button/link to show modal
            $element.click(function(event) {
                event.preventDefault();
                // show modal
                modal.show();
            });

            // TODO: modified to accomodate for count field and include already selected datasets
            // when user preses 'save' button in modal
            modal.$element.on('modalapply', function(event) {
                var $widgetroot = $('#' + settings.widgetid);
                // get selected element
                var $selected = modal.get_selected();
                // we have all the data we need so get rid of the modal
                modal.close();
                if ($selected.length) {
                    var $count = $('input[name="' + settings.widgetname + '.count"]');
                    // update count field to add new selection from modal
                    var count = parseInt($count.val()) || 0;
                    $count.val(count + $selected.length);
                    // collect already selected datasets
                    var params = $widgetroot.find('input,select').serializeArray();
                    // collect newly selected datasets
                    $.each($selected, function(index, value) {
                        params.push({name: settings.widgetname + '.experiment.' + count,
                                     value: $(value).attr('data-uuid')});
                        count += 1;
                    });
                    // add count parameter if it was not on page already
                    if ($count.length == 0) {
                        params.push({name: settings.widgetname + '.count',
                                     value: count});
                    }
                    //fetch html for widget
                    reload_widget(params);
                }
            });

            $('#' + settings.widgetid).on('click', 'a:has(i.icon-remove)',
                function(event){
                    event.preventDefault();
                    $(this).parents('div.selecteditem').remove();
                    // trigger change event on widget update
                    $(event.delegateTarget).trigger('widgetChanged');
                }
            );

            function reload_widget(params) {
                var $widgetroot = $('#' + settings.widgetid);
                $widgetroot.load(
                    settings.widgeturl + ' #' + settings.widgetid + ' >',
                    params,
                    function(text, status, xhr) {
                        // trigger change event when widget has been updated
                        $(this).trigger('widgetChanged');
                        $.each($(this).find('select'), function(index, elem) {
                            $(elem).selectize({create: true,
                                               persist: false});
                        });
                    }
                );
            };
            
            // TODO: this is different to original
            //       there is also a hardcoded reference to another widget this one depends on
            $experiment_type
                .on('change', function(event, par1, par2) {
                    // update settings with new search parameters
                    var exptype = $(this).val();
                    var oldparams = modal.get_initial_filters();
                    // check if params have changed
                    if (exptype != oldparams.experimenttype) {
                        // update the reference
                        oldparams['experimenttype:list'] = [exptype];
                        // clear dependent widget
                        // TODO : shall we reload widget? (to get possible empty input markers)
                        $('#' + settings.widgetid).empty();
                    }
                });

        };

        if (typeof bccvl === 'undefined') {
            bccvl = {};
        }
        $.extend(bccvl, {
            select_dataset: select_dataset,
            select_dataset_dict: select_dataset_dict,
            select_dataset_future: select_dataset_future,
            select_experiment: select_experiment
        });


    }(jQuery)
);
