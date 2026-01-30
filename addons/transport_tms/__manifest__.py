# -*- coding: utf-8 -*-
{
    "name": "transport_tms",
    "summary": "Short (1 phrase/line) summary of the module's purpose",
    "description": """
Long description of module's purpose
    """,
    "author": "Dorii Software",
    "website": "https://www.dorii.in",
    "version": "1.0",
    "category": "Uncategorized",
    "application": True,
    # any module necessary for this one to work correctly
    "depends": ["base", "mail", "stock", "fleet", "ds_accounts"],
    # always loaded
    "data": [
        "security/ir.model.access.csv",
        "views/dummy.xml",
        "views/templates.xml",
        # core
        "views/transport_res_partner_views.xml",
        "views/transport_city_views.xml",
        "views/transport_location_views.xml",
        "views/transport_route_plan_views.xml",
        "views/transport_goods_type_views.xml",
        "views/transport_b2b_rate_views.xml",
        # booking
        "views/transport_booking.xml",
        "views/transport_movement_views.xml",
        "views/transport_manifest_views.xml",
        "views/transport_assign_manifest_wizard_view.xml",
        # inbound-manifest-batch
        "views/transport_inbound_manifest.xml",
        # hub Operation
        "views/transport_hub_receive_wizard_views.xml",
        "views/transport_good_delivery_wizard_views.xml",
        "views/transport_hub_inventory_views.xml",
        ## good delivery"
        "views/transport_good_delivery_views.xml",
        ##---Dashboard
        "views/dashboard_views.xml",
        ## data
        "data/vehicle_manufacturer.xml",
        "data/vehicle_model.xml",
        "data/vehicle_category.xml",
        ## sequences
        "data/sequences.xml",
        ##navigation (last)
        "views/navigation.xml",
    ],
    # only loaded in demonstration mode
    "demo": [
        "demo/demo.xml",
    ],
    "assets": {
        "web.assets_backend": [
            # "transport_tms/static/src/js/dashboard.js",
            # "transport_tms/static/src/xml/dashboard.xml",
        ],
    },
    # migration
    "post_init_hook": "init_chatter_on_existing_manifests",
}
