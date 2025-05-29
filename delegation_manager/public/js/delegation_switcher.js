frappe.after_ajax(function () {
    // Remove previous delegation buttons and modal to avoid duplicates
    $('.delegation-action-btn, #delegation-modal').remove();

    // Helper to create the delegation button
    function make_btn(label, icon) {
        return $(`
            <button class="btn btn-primary delegation-action-btn" style="margin-left:10px; display:flex; align-items:center; height:30px; width:auto;">
                <span class="fa ${icon}" style="margin-right:7px;"></span> ${label}
            </button>
        `);
    }

    // Fetch delegations and update UI
    frappe.call({
        method: 'delegation_manager.api.get_active_delegations',
        freeze: false
    }).then(function (r) {
        let delegations = r.message || [];
        if (delegations.length === 0) return;

        // Find the Awesome Bar/form-inline container
        let awesomeBarContainer = document.querySelector(".collapse > .form-inline") || document.querySelector(".collapse");
        if (!awesomeBarContainer) return;

        // Remove previous delegation button(s) if any
        $(awesomeBarContainer).find('.delegation-action-btn').remove();

        // Only one delegation: show a simple button
        if (delegations.length === 1) {
            let delegation = delegations[0];
            let label, icon, actionFn;
            if (delegation.logged == 1 && delegation.current_user === delegation.delegator) {
                label = "Revert to " + (delegation.delegatee_full_name || delegation.delegatee);
                icon = "fa-undo";
                actionFn = function (e) {
                    e.preventDefault();
                    frappe.call({
                        method: 'delegation_manager.api.revert_identity',
                        args: { delegation_name: delegation.name },
                        freeze: true,
                        freeze_message: __("Switching back to your account...")
                    }).then(function(r) {
                        if (r && r.message && r.message.redirect) {
                            window.location.href = r.message.redirect;
                        } else {
                            window.location.reload();
                        }
                    });
                }
            } else {
                label = "Delegate to " + (delegation.delegator_full_name || delegation.delegator);
                icon = "fa-user-secret";
                actionFn = function (e) {
                    e.preventDefault();
                    frappe.call({
                        method: 'delegation_manager.api.assume_identity',
                        args: { delegation_name: delegation.name },
                        freeze: true,
                        freeze_message: __("Delegating access...")
                    }).then(function(r) {
                        if (r && r.message && r.message.redirect) {
                            window.location.href = r.message.redirect;
                        } else {
                            window.location.reload();
                        }
                    });
                }
            }
            let btn = make_btn(label, icon);
            btn.on('click', actionFn);

            // Place after attendance button if it exists
            let attendanceBtn = awesomeBarContainer.querySelector('.attendance-toggle-button');
            if (attendanceBtn) {
                attendanceBtn.insertAdjacentElement('afterend', btn[0]);
            } else {
                awesomeBarContainer.appendChild(btn[0]);
            }
        }
        // Multiple delegations: show a single "Delegations" button, open modal on click
        else if (delegations.length > 1) {
            let btn = make_btn('Delegations', 'fa-user-secret');
            btn.on('click', function (e) {
                e.preventDefault();
                showDelegationModal(delegations);
            });
            // Place after attendance button if it exists
            let attendanceBtn = awesomeBarContainer.querySelector('.attendance-toggle-button');
            if (attendanceBtn) {
                attendanceBtn.insertAdjacentElement('afterend', btn[0]);
            } else {
                awesomeBarContainer.appendChild(btn[0]);
            }
        }
    });

    // Modal function for delegation selection
    function showDelegationModal(delegations) {
        // Remove any existing modal
        $('#delegation-modal').remove();

        let modal = $(`
            <div class="modal fade" tabindex="-1" role="dialog" id="delegation-modal">
                <div class="modal-dialog" role="document">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h4 class="modal-title">${__("Select Delegation")}</h4>
                            <button type="button" class="close" data-dismiss="modal" aria-label="Close" style="font-size: 2rem;">&times;</button>
                        </div>
                        <div class="modal-body">
                            <ul class="list-group delegation-list"></ul>
                        </div>
                    </div>
                </div>
            </div>
        `);

        delegations.forEach(function (delegation) {
            let label, icon, action, btnClass;
            if (delegation.logged == 1 && delegation.current_user === delegation.delegator) {
                label = "Revert to " + (delegation.delegatee_full_name || delegation.delegatee);
                icon = "fa-undo";
                action = "revert";
                btnClass = "btn-warning";
            } else {
                label = "Delegate to " + (delegation.delegator_full_name || delegation.delegator);
                icon = "fa-user-secret";
                action = "assume";
                btnClass = "btn-primary";
            }
            modal.find('.delegation-list').append(`
                <li class="list-group-item d-flex justify-content-between align-items-center">
                    <span>
                        <span class="fa ${icon}" style="margin-right:7px;"></span>
                        ${label}
                    </span>
                    <button 
                        class="btn ${btnClass} delegation-action" 
                        data-action="${action}" 
                        data-name="${delegation.name}">
                        ${action === "assume" ? __("Delegate") : __("Revert")}
                    </button>
                </li>
            `);
        });

        // Add modal to body and show
        $('body').append(modal);
        modal.modal('show');
    }

    // Handle click for dynamically added modal buttons
    $(document).on('click', '.delegation-action', function (e) {
        e.preventDefault();
        let delegation_name = $(this).data('name');
        let action = $(this).data('action');
        let call_opts = {
            freeze: true,
            freeze_message: action === "assume" ?
                __("Delegating access...") :
                __("Switching back to your account...")
        };
        if (action === "assume") {
            call_opts.method = 'delegation_manager.api.assume_identity';
            call_opts.args = { delegation_name: delegation_name };
        } else if (action === "revert") {
            call_opts.method = 'delegation_manager.api.revert_identity';
            call_opts.args = { delegation_name: delegation_name };
        }
        frappe.call(call_opts).then(function(r) {
            if (r && r.message && r.message.redirect) {
                window.location.href = r.message.redirect;
            } else {
                window.location.reload();
            }
        });
    });

    // Optional: Close modal on successful delegation/revert
    $(document).on('hidden.bs.modal', '#delegation-modal', function () {
        $('#delegation-modal').remove();
    });
});