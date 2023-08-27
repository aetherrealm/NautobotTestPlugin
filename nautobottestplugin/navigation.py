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
                        link="plugins:nautobottestplugin:examplemodel_list",
                        name="Example Model",
                        permissions=["nautobottestplugin.view_examplemodel"],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:nautobottestplugin:examplemodel_add",
                                permissions=[
                                    "nautobottestplugin.add_examplemodel",
                                ],
                            ),
                            NavMenuImportButton(
                                link="plugins:nautobottestplugin:examplemodel_import",
                                permissions=["nautobottestplugin.add_examplemodel"],
                            ),
                        ),
                    ),
                ),
            ),
        ),
    ),
)