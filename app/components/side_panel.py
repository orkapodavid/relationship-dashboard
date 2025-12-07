import reflex as rx
from app.states.relationship_state import RelationshipState


def relationship_item(item: dict) -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.p(
                item["connected_node_name"],
                class_name="font-medium text-gray-900 text-sm truncate",
            ),
            rx.el.div(
                rx.el.span(
                    item["term"].upper(),
                    class_name="text-[10px] font-bold tracking-wider text-gray-500 uppercase mr-2",
                ),
                rx.el.span(
                    rx.cond(
                        item["type"] == "employment",
                        "Struct.",
                        item["score"].to_string(),
                    ),
                    class_name=rx.cond(
                        item["type"] == "employment",
                        "px-1.5 py-0.5 rounded text-[10px] font-semibold bg-gray-100 text-gray-600 border border-gray-200",
                        "px-1.5 py-0.5 rounded text-[10px] font-semibold "
                        + item["badge_class"],
                    ),
                ),
                class_name="flex items-center mt-0.5",
            ),
            class_name="flex-1 min-w-0",
        ),
        rx.el.button(
            rx.icon("trash", class_name="w-3.5 h-3.5"),
            on_click=lambda: RelationshipState.soft_delete_relationship(
                item["relationship_id"]
            ),
            class_name="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-md transition-colors",
        ),
        class_name="flex items-center justify-between p-3 bg-white border border-gray-100 rounded-lg hover:border-indigo-100 transition-colors",
    )


def node_creation_view() -> rx.Component:
    return rx.el.div(
        rx.el.h2(
            "New Entity",
            class_name="text-xl font-bold mb-6 text-gray-900 border-b pb-2",
        ),
        rx.el.div(
            rx.el.label(
                "Type", class_name="text-sm font-medium text-gray-500 mb-2 block"
            ),
            rx.el.div(
                rx.el.label(
                    rx.el.input(
                        type="radio",
                        name="node_type",
                        value="person",
                        checked=RelationshipState.new_node_type == "person",
                        on_change=lambda _: RelationshipState.set_new_node_type(
                            "person"
                        ),
                        class_name="w-4 h-4 text-indigo-600 focus:ring-indigo-500 border-gray-300",
                    ),
                    rx.el.span("Person", class_name="ml-2 text-sm text-gray-700"),
                    class_name="flex items-center",
                ),
                rx.el.label(
                    rx.el.input(
                        type="radio",
                        name="node_type",
                        value="company",
                        checked=RelationshipState.new_node_type == "company",
                        on_change=lambda _: RelationshipState.set_new_node_type(
                            "company"
                        ),
                        class_name="w-4 h-4 text-indigo-600 focus:ring-indigo-500 border-gray-300",
                    ),
                    rx.el.span("Company", class_name="ml-2 text-sm text-gray-700"),
                    class_name="flex items-center",
                ),
                class_name="flex gap-6 mb-6",
            ),
            rx.cond(
                RelationshipState.new_node_type == "person",
                rx.el.div(
                    rx.el.label(
                        "First Name *",
                        class_name="text-sm font-medium text-gray-500 mb-1 block",
                    ),
                    rx.el.input(
                        on_change=RelationshipState.set_new_node_name,
                        class_name="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm mb-4 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none",
                        default_value=RelationshipState.new_node_name,
                    ),
                    rx.el.label(
                        "Last Name",
                        class_name="text-sm font-medium text-gray-500 mb-1 block",
                    ),
                    rx.el.input(
                        on_change=RelationshipState.set_new_node_last_name,
                        class_name="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm mb-4 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none",
                        default_value=RelationshipState.new_node_last_name,
                    ),
                    rx.el.label(
                        "Job Title",
                        class_name="text-sm font-medium text-gray-500 mb-1 block",
                    ),
                    rx.el.input(
                        on_change=RelationshipState.set_new_node_title_or_ticker,
                        class_name="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm mb-6 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none",
                        default_value=RelationshipState.new_node_title_or_ticker,
                    ),
                ),
                rx.el.div(
                    rx.el.label(
                        "Company Name *",
                        class_name="text-sm font-medium text-gray-500 mb-1 block",
                    ),
                    rx.el.input(
                        on_change=RelationshipState.set_new_node_name,
                        class_name="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm mb-4 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none",
                        default_value=RelationshipState.new_node_name,
                    ),
                    rx.el.label(
                        "Ticker / ID",
                        class_name="text-sm font-medium text-gray-500 mb-1 block",
                    ),
                    rx.el.input(
                        on_change=RelationshipState.set_new_node_title_or_ticker,
                        class_name="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm mb-6 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none",
                        default_value=RelationshipState.new_node_title_or_ticker,
                    ),
                ),
            ),
            rx.el.button(
                rx.cond(
                    RelationshipState.is_loading,
                    rx.el.span("Saving...", class_name="animate-pulse"),
                    "Create Entity",
                ),
                on_click=RelationshipState.save_node,
                disabled=RelationshipState.is_loading,
                class_name="w-full bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-semibold py-2.5 px-4 rounded-lg transition-colors shadow-sm mb-3",
            ),
            rx.el.button(
                "Cancel",
                on_click=RelationshipState.cancel_node_creation,
                class_name="w-full bg-white hover:bg-gray-50 text-gray-700 font-medium py-2.5 px-4 rounded-lg border border-gray-300 transition-colors",
            ),
            class_name="flex-1 overflow-y-auto",
        ),
        class_name="p-6 h-full flex flex-col bg-white",
    )


def node_edit_view() -> rx.Component:
    return rx.el.div(
        rx.el.h2(
            "Edit Entity",
            class_name="text-xl font-bold mb-6 text-gray-900 border-b pb-2",
        ),
        rx.el.div(
            rx.cond(
                RelationshipState.editing_node_type == "person",
                rx.el.div(
                    rx.el.label(
                        "First Name",
                        class_name="text-sm font-medium text-gray-500 mb-1 block",
                    ),
                    rx.el.input(
                        default_value=RelationshipState.editing_node_data["first_name"],
                        on_change=lambda val: RelationshipState.set_editing_node_data(
                            {"first_name": val}
                        ),
                        class_name="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm mb-4 focus:ring-2 focus:ring-indigo-500 outline-none",
                    ),
                    rx.el.label(
                        "Last Name",
                        class_name="text-sm font-medium text-gray-500 mb-1 block",
                    ),
                    rx.el.input(
                        default_value=RelationshipState.editing_node_data["last_name"],
                        on_change=lambda val: RelationshipState.set_editing_node_data(
                            {"last_name": val}
                        ),
                        class_name="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm mb-4 focus:ring-2 focus:ring-indigo-500 outline-none",
                    ),
                    rx.el.label(
                        "Job Title",
                        class_name="text-sm font-medium text-gray-500 mb-1 block",
                    ),
                    rx.el.input(
                        default_value=RelationshipState.editing_node_data["job_title"],
                        on_change=lambda val: RelationshipState.set_editing_node_data(
                            {"job_title": val}
                        ),
                        class_name="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm mb-6 focus:ring-2 focus:ring-indigo-500 outline-none",
                    ),
                ),
                rx.el.div(
                    rx.el.label(
                        "Company Name",
                        class_name="text-sm font-medium text-gray-500 mb-1 block",
                    ),
                    rx.el.input(
                        default_value=RelationshipState.editing_node_data["name"],
                        on_change=lambda val: RelationshipState.set_editing_node_data(
                            {"name": val}
                        ),
                        class_name="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm mb-4 focus:ring-2 focus:ring-indigo-500 outline-none",
                    ),
                    rx.el.label(
                        "Ticker",
                        class_name="text-sm font-medium text-gray-500 mb-1 block",
                    ),
                    rx.el.input(
                        default_value=RelationshipState.editing_node_data["ticker"],
                        on_change=lambda val: RelationshipState.set_editing_node_data(
                            {"ticker": val}
                        ),
                        class_name="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm mb-6 focus:ring-2 focus:ring-indigo-500 outline-none",
                    ),
                ),
            ),
            rx.el.button(
                rx.cond(
                    RelationshipState.is_loading,
                    rx.el.span("Saving...", class_name="animate-pulse"),
                    "Save Changes",
                ),
                on_click=RelationshipState.save_node,
                disabled=RelationshipState.is_loading,
                class_name="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-2.5 px-4 rounded-lg transition-colors shadow-sm mb-3",
            ),
            rx.el.button(
                "Cancel",
                on_click=RelationshipState.cancel_edit,
                class_name="w-full bg-white hover:bg-gray-50 text-gray-700 font-medium py-2.5 px-4 rounded-lg border border-gray-300 transition-colors mb-6",
            ),
            rx.el.div(
                rx.el.button(
                    rx.icon("trash-2", class_name="w-4 h-4 mr-2"),
                    "Delete Entity",
                    on_click=lambda: RelationshipState.delete_node(
                        RelationshipState.editing_node_id,
                        RelationshipState.editing_node_type,
                    ),
                    class_name="w-full flex items-center justify-center bg-white border border-red-200 text-red-600 hover:bg-red-50 font-semibold py-2.5 px-4 rounded-lg transition-colors",
                ),
                class_name="mt-auto pt-6 border-t",
            ),
            class_name="flex-1 overflow-y-auto flex flex-col",
        ),
        class_name="p-6 h-full flex flex-col",
    )


def relationship_creation_view() -> rx.Component:
    return rx.el.div(
        rx.el.h2(
            "Add Connection",
            class_name="text-xl font-bold mb-6 text-gray-900 border-b pb-2",
        ),
        rx.el.div(
            rx.el.label(
                "Search Target Node",
                class_name="text-sm font-medium text-gray-500 mb-2 block",
            ),
            rx.el.input(
                placeholder="Type name...",
                on_change=lambda v: RelationshipState.filter_target_nodes(v).throttle(
                    300
                ),
                class_name="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm mb-2 focus:ring-2 focus:ring-indigo-500 outline-none",
                default_value=RelationshipState.relationship_target_search,
            ),
            rx.cond(
                RelationshipState.filtered_target_nodes.length() > 0,
                rx.el.div(
                    rx.foreach(
                        RelationshipState.filtered_target_nodes,
                        lambda node: rx.el.button(
                            rx.el.div(
                                rx.el.span(
                                    node["name"],
                                    class_name="font-medium text-gray-900 block truncate",
                                ),
                                rx.el.span(
                                    node["subtitle"],
                                    class_name="text-xs text-gray-500 block truncate",
                                ),
                                class_name="flex-1 text-left min-w-0",
                            ),
                            rx.el.span(
                                node["type"],
                                class_name="ml-2 text-[10px] uppercase font-bold text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded",
                            ),
                            on_click=lambda: RelationshipState.set_creation_target(
                                node["id"], node["type"], node["name"]
                            ),
                            class_name="w-full flex items-center p-2 hover:bg-indigo-50 rounded-md transition-colors text-sm border-b border-gray-50 last:border-0",
                        ),
                    ),
                    class_name="max-h-40 overflow-y-auto border border-gray-200 rounded-lg mb-4 bg-white shadow-sm",
                ),
                rx.el.p(
                    "Type to search for people or companies...",
                    class_name="text-xs text-gray-400 mb-4 italic",
                ),
            ),
            rx.cond(
                RelationshipState.creation_target_id != 0,
                rx.el.div(
                    rx.el.div(
                        rx.el.span("Target:", class_name="text-gray-500 mr-2"),
                        rx.el.span(
                            RelationshipState.creation_target_name,
                            class_name="font-bold text-indigo-600",
                        ),
                        class_name="text-sm mb-4 p-2 bg-indigo-50 rounded-md border border-indigo-100",
                    ),
                    rx.el.label(
                        "Relationship Term",
                        class_name="text-sm font-medium text-gray-500 mb-2 block",
                    ),
                    rx.el.select(
                        rx.foreach(
                            RelationshipState.relationship_terms,
                            lambda t: rx.el.option(t, value=t),
                        ),
                        value=RelationshipState.creation_term,
                        on_change=RelationshipState.set_creation_term,
                        class_name="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm mb-4 focus:ring-2 focus:ring-indigo-500 bg-white",
                    ),
                    rx.el.label(
                        "Initial Score",
                        class_name="text-sm font-medium text-gray-500 mb-2 block",
                    ),
                    rx.el.input(
                        type="range",
                        min="-100",
                        max="100",
                        default_value=RelationshipState.creation_score.to_string(),
                        key=RelationshipState.creation_term,
                        on_change=lambda v: RelationshipState.set_creation_score(
                            v.to(int)
                        ).throttle(100),
                        class_name="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer mb-2 accent-indigo-600",
                    ),
                    rx.el.div(
                        RelationshipState.creation_score,
                        class_name="text-center font-mono font-bold text-gray-700 text-sm mb-6",
                    ),
                    rx.el.button(
                        "Confirm Connection",
                        on_click=RelationshipState.create_relationship_from_panel,
                        class_name="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-2.5 px-4 rounded-lg transition-colors shadow-sm mb-3",
                    ),
                    class_name="animate-in fade-in slide-in-from-top-2 duration-300",
                ),
            ),
            rx.el.button(
                "Cancel",
                on_click=RelationshipState.cancel_relationship_creation,
                class_name="w-full bg-white hover:bg-gray-50 text-gray-700 font-medium py-2.5 px-4 rounded-lg border border-gray-300 transition-colors mt-auto",
            ),
            class_name="flex-1 overflow-y-auto flex flex-col",
        ),
        class_name="p-6 h-full flex flex-col",
    )


def node_details_view() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.h2("Details", class_name="text-xl font-bold text-gray-900"),
            rx.el.span(
                rx.cond(
                    RelationshipState.selected_node_data["type"] == "company",
                    "Company",
                    "Person",
                ),
                class_name="text-xs font-bold uppercase tracking-wider text-indigo-500 bg-indigo-50 px-2 py-1 rounded-full",
            ),
            class_name="flex items-center justify-between mb-6 border-b pb-2 shrink-0",
        ),
        rx.el.div(
            rx.el.div(
                rx.el.label(
                    "Name",
                    class_name="text-xs font-bold text-gray-400 uppercase mb-1 block",
                ),
                rx.el.p(
                    RelationshipState.selected_node_data["display_name"],
                    class_name="text-lg font-semibold text-gray-900 mb-4 whitespace-pre-wrap",
                ),
                rx.el.label(
                    "Role / Info",
                    class_name="text-xs font-bold text-gray-400 uppercase mb-1 block",
                ),
                rx.el.p(
                    RelationshipState.selected_node_data["job"],
                    class_name="text-base text-gray-700 mb-6",
                ),
                rx.el.div(
                    rx.el.button(
                        rx.icon("pencil", class_name="w-4 h-4 mr-2"),
                        "Edit Details",
                        on_click=RelationshipState.prepare_node_edit,
                        class_name="flex-1 flex items-center justify-center bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 font-medium py-2 px-3 rounded-lg transition-colors text-sm",
                    ),
                    rx.el.button(
                        rx.icon("plus", class_name="w-4 h-4 mr-2"),
                        "Add Link",
                        on_click=RelationshipState.start_relationship_creation,
                        class_name="flex-1 flex items-center justify-center bg-indigo-600 hover:bg-indigo-700 text-white font-medium py-2 px-3 rounded-lg transition-colors text-sm",
                    ),
                    class_name="flex gap-3 mb-8",
                ),
                class_name="shrink-0",
            ),
            rx.el.div(
                rx.el.h3(
                    "Connections",
                    class_name="text-sm font-bold text-gray-900 mb-3 flex items-center gap-2",
                ),
                rx.cond(
                    RelationshipState.active_node_relationships.length() > 0,
                    rx.el.div(
                        rx.foreach(
                            RelationshipState.active_node_relationships,
                            relationship_item,
                        ),
                        class_name="space-y-2",
                    ),
                    rx.el.div(
                        rx.icon(
                            "users", class_name="w-8 h-8 text-gray-300 mb-2 mx-auto"
                        ),
                        rx.el.p(
                            "No active connections",
                            class_name="text-sm text-gray-400 text-center",
                        ),
                        class_name="py-8 bg-gray-50 rounded-lg border border-dashed border-gray-200",
                    ),
                ),
                class_name="flex-1 overflow-y-auto mb-4",
            ),
            rx.el.div(class_name="border-t border-gray-200 my-6"),
            rx.el.div(
                rx.el.h3(
                    "Record Metadata", class_name="text-sm font-bold text-gray-900 mb-4"
                ),
                rx.el.label(
                    "Modified By",
                    class_name="text-xs font-medium text-gray-500 mb-1 block",
                ),
                rx.el.input(
                    read_only=True,
                    class_name="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm mb-3 bg-gray-50 text-gray-600 cursor-not-allowed",
                    default_value=RelationshipState.selected_node_data[
                        "last_modified_by"
                    ],
                    key=RelationshipState.selected_node_id.to_string() + "_mod_by",
                ),
                rx.el.label(
                    "Operation Type",
                    class_name="text-xs font-medium text-gray-500 mb-1 block",
                ),
                rx.el.input(
                    read_only=True,
                    class_name="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm mb-3 bg-gray-50 text-gray-600 cursor-not-allowed",
                    default_value=RelationshipState.selected_node_data[
                        "operation_type"
                    ],
                    key=RelationshipState.selected_node_id.to_string() + "_op_type",
                ),
                rx.el.label(
                    "Last Updated",
                    class_name="text-xs font-medium text-gray-500 mb-1 block",
                ),
                rx.el.input(
                    read_only=True,
                    class_name="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-gray-50 text-gray-600 cursor-not-allowed",
                    default_value=RelationshipState.selected_node_data["updated_at"],
                    key=RelationshipState.selected_node_id.to_string() + "_ts",
                ),
                class_name="shrink-0",
            ),
            rx.el.div(
                rx.el.button(
                    rx.icon("trash-2", class_name="w-4 h-4 mr-2"),
                    "Delete Entity",
                    on_click=RelationshipState.delete_current_selection,
                    class_name="w-full flex items-center justify-center bg-white border border-red-200 text-red-600 hover:bg-red-50 font-semibold py-2.5 px-4 rounded-lg transition-colors",
                ),
                class_name="mt-auto pt-6 border-t",
            ),
            class_name="flex-1 flex flex-col min-h-0",
        ),
        class_name="p-6 h-full flex flex-col",
    )


def edge_edit_view() -> rx.Component:
    return rx.el.div(
        rx.el.div(
            rx.el.h2("Edit Relationship", class_name="text-xl font-bold text-gray-900"),
            class_name="mb-6 border-b pb-2 shrink-0",
        ),
        rx.el.div(
            rx.el.div(
                rx.el.span(
                    "Type:", class_name="text-sm font-medium text-gray-500 mr-2"
                ),
                rx.el.span(
                    RelationshipState.editing_relationship_type.upper(),
                    class_name="px-2 py-1 rounded-full text-xs font-bold bg-gray-100 text-gray-800 border border-gray-200",
                ),
                rx.cond(
                    RelationshipState.editing_is_directed,
                    rx.el.span(
                        "Directed →",
                        class_name="px-2 py-1 rounded-full text-xs font-bold bg-blue-50 text-blue-700 border border-blue-100",
                    ),
                    rx.el.span(
                        "Mutual ↔",
                        class_name="px-2 py-1 rounded-full text-xs font-bold bg-purple-50 text-purple-700 border border-purple-100",
                    ),
                ),
                class_name="mb-6 flex items-center flex-wrap gap-2",
            ),
            rx.cond(
                RelationshipState.editing_relationship_type == "employment",
                rx.el.div(
                    rx.icon(
                        "briefcase", class_name="w-12 h-12 text-gray-300 mx-auto mb-3"
                    ),
                    rx.el.p(
                        "Employment relationships are structural links.",
                        class_name="text-center text-gray-600 font-medium mb-1",
                    ),
                    rx.el.p(
                        "They do not carry a sentiment score.",
                        class_name="text-center text-gray-400 text-sm",
                    ),
                    class_name="bg-gray-50 rounded-lg p-6 border border-gray-100 mb-6",
                ),
                rx.el.div(
                    rx.el.label(
                        "Nature of Relationship",
                        class_name="text-sm font-medium text-gray-500 mb-2 block",
                    ),
                    rx.el.select(
                        rx.foreach(
                            RelationshipState.relationship_terms,
                            lambda t: rx.el.option(t, value=t),
                        ),
                        value=RelationshipState.editing_term,
                        on_change=RelationshipState.handle_term_change,
                        class_name="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm mb-6 focus:outline-none focus:ring-2 focus:ring-indigo-500 bg-white",
                    ),
                    rx.el.label(
                        "Relationship Score",
                        class_name="text-sm font-medium text-gray-500 mb-4 block",
                    ),
                    rx.el.div(
                        rx.el.span(
                            "-100 (Enemy)", class_name="text-xs font-bold text-red-500"
                        ),
                        rx.el.span(
                            "0 (Neutral)", class_name="text-xs font-bold text-gray-500"
                        ),
                        rx.el.span(
                            "+100 (Ally)", class_name="text-xs font-bold text-green-500"
                        ),
                        class_name="flex justify-between w-full mb-2 px-1",
                    ),
                    rx.el.input(
                        type="range",
                        min="-100",
                        max="100",
                        default_value=RelationshipState.editing_score.to_string(),
                        key=RelationshipState.selected_edge_id,
                        on_change=lambda value: RelationshipState.set_editing_score(
                            value.to(int)
                        ).throttle(100),
                        class_name="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer mb-4 accent-indigo-600",
                    ),
                    rx.el.div(
                        "Current Score: ",
                        rx.el.span(
                            RelationshipState.editing_score,
                            class_name="font-mono font-bold ml-1",
                        ),
                        class_name="text-center text-sm text-gray-600 mb-8",
                    ),
                    rx.el.button(
                        "Save Changes",
                        on_click=RelationshipState.save_relationship_update,
                        class_name="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-3 px-4 rounded-lg transition-colors shadow-sm mb-6",
                    ),
                    class_name="flex flex-col",
                ),
            ),
            rx.el.div(
                rx.el.button(
                    rx.icon("trash", class_name="w-4 h-4 mr-2"),
                    "Delete Relationship",
                    on_click=lambda: RelationshipState.soft_delete_relationship(
                        RelationshipState.selected_edge_id.split("-")[1].to(int)
                    ),
                    class_name="w-full flex items-center justify-center bg-white border border-red-200 text-red-600 hover:bg-red-50 font-semibold py-3 px-4 rounded-lg transition-colors",
                ),
                class_name="mt-auto pt-4 border-t",
            ),
            class_name="flex-1 overflow-y-auto flex flex-col",
        ),
        class_name="p-6 h-full flex flex-col",
    )


def side_panel() -> rx.Component:
    return rx.el.aside(
        rx.el.div(
            rx.cond(RelationshipState.node_create_mode, node_creation_view()),
            rx.cond(
                ~RelationshipState.node_create_mode
                & RelationshipState.is_creating_relationship,
                relationship_creation_view(),
            ),
            rx.cond(
                ~RelationshipState.node_create_mode
                & ~RelationshipState.is_creating_relationship
                & (RelationshipState.edit_mode == "node")
                & RelationshipState.is_editing,
                node_edit_view(),
            ),
            rx.cond(
                ~RelationshipState.node_create_mode
                & ~RelationshipState.is_creating_relationship
                & (RelationshipState.edit_mode == "node")
                & ~RelationshipState.is_editing,
                node_details_view(),
            ),
            rx.cond(
                ~RelationshipState.node_create_mode
                & ~RelationshipState.is_creating_relationship
                & (RelationshipState.edit_mode == "edge"),
                edge_edit_view(),
            ),
            class_name="flex-1 w-full h-full bg-white relative z-50",
        ),
        class_name=rx.cond(
            RelationshipState.show_side_panel,
            "fixed top-0 right-0 h-full w-96 bg-white shadow-2xl z-[10000] transform transition-transform duration-300 ease-in-out translate-x-0 border-l border-gray-200 flex flex-col",
            "fixed top-0 right-0 h-full w-96 bg-white shadow-2xl z-[10000] transform transition-transform duration-300 ease-in-out translate-x-full border-l border-gray-200 flex flex-col",
        ),
        custom_attrs={"aria-label": "Side Panel"},
    )