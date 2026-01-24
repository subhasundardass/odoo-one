/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

class TransportDashboard extends Component {
    setup() {
        this.rpc = useService("rpc");
        this.state = useState({ data: {} });

        onWillStart(async () => {
            this.state.data = await this.rpc({
                model: "transport.dashboard",
                method: "get_dashboard_data",
                args: [],
                kwargs: {},
            });
        });
    }
}

TransportDashboard.template = "transport_dashboard_template";

/**
 * ✅ THIS WRAPPER IS REQUIRED
 */
const TransportDashboardAction = {
    Component: TransportDashboard,
};

/**
 * ✅ CORRECT ODOO 17 CLIENT ACTION
 */
// registry.category("actions").add("transport_dashboard", (env, action) => {
//     return {
//         Component: TransportDashboard,
//         props: {},
//     };
// });

registry.category("actions").add(
    "transport_dashboard",
    TransportDashboard
);