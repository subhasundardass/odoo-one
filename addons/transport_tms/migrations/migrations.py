from odoo import api, SUPERUSER_ID
from odoo.tools import mute_logger


@mute_logger("odoo.sql_db")
def init_chatter_on_existing_manifests(cr, registry):
    """
    Migration script to initialize chatter for existing transport.manifest records.
    Adds mail.thread & mail.activity.mixin fields if missing.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})

    # Step 1: Ensure the table has the required JSONB columns
    cr.execute(
        """
        ALTER TABLE transport_manifest
        ADD COLUMN IF NOT EXISTS message_ids jsonb,
        ADD COLUMN IF NOT EXISTS message_follower_ids jsonb,
        ADD COLUMN IF NOT EXISTS activity_ids jsonb;
    """
    )

    # Step 2: Initialize existing records so chatter works
    manifests = env["transport.manifest"].search([])
    for manifest in manifests:
        # Only set if None to avoid overwriting existing messages
        if manifest.message_ids is None:
            manifest.message_ids = []
        if manifest.message_follower_ids is None:
            manifest.message_follower_ids = []
        if manifest.activity_ids is None:
            manifest.activity_ids = []

    env.cr.commit()
    _logger = env["ir.logging"].sudo()
    _logger.create(
        {
            "name": "Migration",
            "type": "server",
            "dbname": env.cr.dbname,
            "level": "INFO",
            "message": f"Initialized chatter on {len(manifests)} transport.manifest records",
            "path": "init_chatter_on_existing_manifests",
            "func": "post_init_hook",
            "line": 0,
        }
    )
