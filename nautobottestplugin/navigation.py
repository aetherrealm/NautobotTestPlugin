from nautobot.core.apps import (
    NavMenuAddButton,
    NavMenuGroup,
    NavMenuItem,
    NavMenuImportButton,
    NavMenuTab
)
menu_items = (
    NavMenuTab(
        name="DCN",
        weight=350,
        groups=(
            NavMenuGroup(
                name="Wizards",
                weight=100,
                items=(
                    NavMenuItem(
                        link="",
                        name="DCN Home",
                        permissions=["nautobottestplugin.view_examplemodel"]
                    ),
                ),
            ),
        ),
    ),
)