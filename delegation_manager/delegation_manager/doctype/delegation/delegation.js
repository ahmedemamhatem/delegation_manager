frappe.ui.form.on('Delegation', {
    refresh: function(frm) {
        // Only for submitted docs, System Manager users, in Form view
        if (
            frm.doc.docstatus === 1 &&
            frappe.user_roles.includes('System Manager')
        ) {
            frm.clear_custom_buttons();

            // ➕ Add Message Rule
            frm.add_custom_button('➕ Add Message Rule', function() {
                frappe.call({
                    method: 'delegation_manager.email.create_message_rule',
                    args: { delegation: frm.doc.name },
                    freeze: true,
                    freeze_message: __('Creating message rule...'),
                    callback: function(r) {
                        show_py_response(r);
                        frm.reload_doc();
                    }
                });
            });

            // 🔄 Fetch Message Rules
            frm.add_custom_button('🔄 Fetch Message Rules', function() {
                frappe.call({
                    method: 'delegation_manager.email.get_message_rules',
                    args: { delegation: frm.doc.name },
                    freeze: true,
                    freeze_message: __('Fetching message rules...'),
                    callback: function(r) {
                        show_py_response(r);
                        frm.reload_doc();
                    }
                });
            });

            // 🗑️ Remove Message Rule(s)
            frm.add_custom_button('🗑️ Remove Message Rule(s)', function() {
                frappe.call({
                    method: 'delegation_manager.email.delete_message_rule',
                    args: { delegation: frm.doc.name },
                    freeze: true,
                    freeze_message: __('Deleting message rule(s)...'),
                    callback: function(r) {
                        show_py_response(r);
                        frm.reload_doc();
                    }
                });
            });
        } else {
            frm.clear_custom_buttons();
        }

        // Helper to print Python response nicely
        function show_py_response(r) {
            if (!r || r.exc) {
                return;
            }
            // If r.message is an object with a .message property, print just that
            if (typeof r.message === 'object' && r.message && r.message.message) {
                frappe.msgprint(r.message.message);
            }
            // If r.message is a string, print it
            else if (typeof r.message === 'string') {
                frappe.msgprint(r.message);
            }
            // If r.message is an object (like your messageRule), print "Success" or any property you wish
            else if (typeof r.message === 'object' && r.message) {
                // Print displayName if present, else generic success
                if (r.message.displayName) {
                    frappe.msgprint(__('Success. Rule: ') + r.message.displayName);
                } else {
                    frappe.msgprint(__('Success'));
                }
            }
            else {
                frappe.msgprint(__('Success'));
            }
        }
            }
});