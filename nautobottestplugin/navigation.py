from nautobot.core.apps import (
    NavMenuAddButton,
    NavMenuGroup,
    NavMenuItem,
    NavMenuImportButton,
    NavMenuTab
)
menu_items = (
    NavMenuTab(
        name="NOC",
        weight=1,
        groups=(
            NavMenuGroup(
                name="DCN",
                weight=100,
                items=(
                    NavMenuItem(
                        link="plugins:nautobottestplugin:dcn_home",
                        name="Operations",
                        permissions=["nautobottestplugin.view_examplemodel"]
                    ),
                ),
            ),
        ),
    ),
)