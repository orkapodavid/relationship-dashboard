import reflex as rx
import sqlmodel
from sqlmodel import select, or_, col, delete
import math
from typing import Optional, TypedDict
from datetime import datetime
import logging
from collections import Counter, defaultdict
from app.models import (
    Account,
    Contact,
    Relationship,
    RelationshipLog,
    RelationshipType,
    RelationshipTerm,
)

TERM_DEFAULTS = {
    RelationshipTerm.WORKS_FOR: {"is_directed": True, "default_score": 0},
    RelationshipTerm.INVESTED_IN: {"is_directed": True, "default_score": 50},
    RelationshipTerm.COMPETITOR: {"is_directed": False, "default_score": -50},
    RelationshipTerm.COLLEAGUE: {"is_directed": False, "default_score": 20},
    RelationshipTerm.FRIEND: {"is_directed": False, "default_score": 80},
    RelationshipTerm.ENEMY: {"is_directed": False, "default_score": -100},
}
TERM_TO_TYPE = {
    RelationshipTerm.WORKS_FOR: RelationshipType.EMPLOYMENT,
    RelationshipTerm.INVESTED_IN: RelationshipType.BUSINESS,
    RelationshipTerm.COMPETITOR: RelationshipType.BUSINESS,
    RelationshipTerm.COLLEAGUE: RelationshipType.BUSINESS,
    RelationshipTerm.FRIEND: RelationshipType.SOCIAL,
    RelationshipTerm.ENEMY: RelationshipType.SOCIAL,
}


class RelationshipItem(TypedDict):
    relationship_id: int
    score: int
    term: str
    is_directed: bool
    connected_node_id: int
    connected_node_type: str
    connected_node_name: str
    type: str
    badge_class: str


class RelationshipState(rx.State):
    """State management for the Relationship Dashboard."""

    accounts: list[Account] = []
    contacts: list[Contact] = []
    relationships: list[Relationship] = []
    filtered_accounts: list[Account] = []
    filtered_contacts: list[Contact] = []
    filtered_relationships: list[Relationship] = []
    selected_account: Optional[Account] = None
    search_query: str = ""
    node_limit: int = 100
    show_add_contact_modal: bool = False
    new_contact_first_name: str = ""
    new_contact_last_name: str = ""
    new_contact_job_title: str = ""
    contact_notes: dict[int, str] = {}
    selected_node_id: str = ""
    selected_edge_id: str = ""
    show_side_panel: bool = False
    edit_mode: str = "none"
    selected_node_data: dict = {}
    is_editing: bool = False
    is_creating_relationship: bool = False
    node_create_mode: bool = False
    editing_node_id: int = 0
    editing_node_type: str = ""
    active_node_relationships: list[RelationshipItem] = []
    creation_target_id: int = 0
    creation_target_type: str = ""
    creation_target_name: str = ""
    creation_term: str = "friend"
    creation_score: int = 0
    editing_node_data: dict = {}
    relationship_target_search: str = ""
    filtered_target_nodes: list[dict] = []
    new_node_type: str = "person"
    new_node_name: str = ""
    new_node_last_name: str = ""
    new_node_title_or_ticker: str = ""
    editing_score: int = 0
    editing_relationship_type: str = ""
    editing_term: str = ""
    editing_is_directed: bool = True
    is_loading: bool = False
    zoom_level: float = 1.0
    show_historic: bool = False
    current_user: str = "System User"
    last_operation_type: str = ""
    last_operation_timestamp: str = ""

    @rx.var
    def relationship_terms(self) -> list[str]:
        """Return list of available relationship terms."""
        return [t.value for t in RelationshipTerm]

    @rx.event
    def toggle_historic(self, value: bool):
        """Toggle visibility of historic/deleted relationships."""
        self.show_historic = value
        yield RelationshipState.load_data

    @rx.event
    def set_new_node_type(self, value: str):
        self.new_node_type = value

    @rx.event
    def set_new_node_name(self, value: str):
        self.new_node_name = value

    @rx.event
    def set_new_node_last_name(self, value: str):
        self.new_node_last_name = value

    @rx.event
    def set_new_node_title_or_ticker(self, value: str):
        self.new_node_title_or_ticker = value

    @rx.event
    def set_editing_node_data(self, updates: dict):
        self.editing_node_data = {**self.editing_node_data, **updates}

    @rx.event
    def handle_term_change(self, new_term: str):
        """Handle term change from UI dropdown."""
        try:
            if self.selected_edge_id.startswith("rel-"):
                rel_id = int(self.selected_edge_id.split("-")[1])
                self.update_relationship_term(rel_id, new_term)
        except Exception as e:
            logging.exception(f"Error handling term change: {e}")

    @rx.event
    async def load_data(self):
        """Load data based on search/filter state."""
        self.is_loading = True
        yield
        try:
            with rx.session() as session:
                sqlmodel.SQLModel.metadata.create_all(session.get_bind())
                if not session.exec(select(Account)).first() and (
                    not session.exec(select(Contact)).first()
                ):
                    self.seed_database()
            if self.search_query.strip():
                self.search_and_build_subgraph(self.search_query)
            else:
                self.get_most_connected_nodes(self.node_limit)
        except Exception as e:
            logging.exception(f"Database error in load_data: {e}")
        finally:
            self.is_loading = False

    @rx.event
    def clear_search(self):
        """Clear the search query and reset view."""
        self.search_query = ""
        yield RelationshipState.load_data

    @rx.event
    def get_most_connected_nodes(self, limit: int):
        """Fetch the top N most connected nodes and their immediate relationships."""
        with rx.session() as session:
            query = select(Relationship)
            if not self.show_historic:
                query = query.where(Relationship.is_active == True)
            rels = session.exec(query).all()
            counter = Counter()
            for r in rels:
                counter[r.source_type, r.source_id] += 1
                counter[r.target_type, r.target_id] += 1
            top_nodes = [node for node, count in counter.most_common(limit)]
            top_node_set = set(top_nodes)
            acc_ids = {nid for ntype, nid in top_node_set if ntype == "company"}
            con_ids = {nid for ntype, nid in top_node_set if ntype == "person"}
            self.filtered_accounts = []
            self.filtered_contacts = []
            if acc_ids:
                self.filtered_accounts = session.exec(
                    select(Account).where(Account.id.in_(acc_ids))
                ).all()
            if con_ids:
                self.filtered_contacts = session.exec(
                    select(Contact).where(Contact.id.in_(con_ids))
                ).all()
            self.filtered_relationships = [
                r
                for r in rels
                if (r.source_type, r.source_id) in top_node_set
                and (r.target_type, r.target_id) in top_node_set
            ]

    @rx.event
    def search_and_build_subgraph(self, query: str):
        """Search for nodes and build a 2-degree subgraph around matches."""
        with rx.session() as session:
            acc_matches = session.exec(
                select(Account).where(col(Account.name).ilike(f"%{query}%"))
            ).all()
            con_matches = session.exec(
                select(Contact).where(
                    or_(
                        col(Contact.first_name).ilike(f"%{query}%"),
                        col(Contact.last_name).ilike(f"%{query}%"),
                    )
                )
            ).all()
            if not acc_matches and (not con_matches):
                self.filtered_accounts = []
                self.filtered_contacts = []
                self.filtered_relationships = []
                return
            frontier = set()
            for a in acc_matches:
                frontier.add(("company", a.id))
            for c in con_matches:
                frontier.add(("person", c.id))
            visited = set(frontier)
            query = select(Relationship)
            if not self.show_historic:
                query = query.where(Relationship.is_active == True)
            all_rels = session.exec(query).all()
            adj = defaultdict(list)
            for r in all_rels:
                src = (r.source_type, r.source_id)
                tgt = (r.target_type, r.target_id)
                adj[src].append(tgt)
                adj[tgt].append(src)
            current_level_nodes = frontier
            for _ in range(2):
                next_level_nodes = set()
                for node in current_level_nodes:
                    for neighbor in adj[node]:
                        if neighbor not in visited:
                            visited.add(neighbor)
                            next_level_nodes.add(neighbor)
                if len(visited) >= self.node_limit:
                    break
                current_level_nodes = next_level_nodes
            if len(visited) > self.node_limit:
                visited = set(list(visited)[: self.node_limit])
            final_acc_ids = {nid for ntype, nid in visited if ntype == "company"}
            final_con_ids = {nid for ntype, nid in visited if ntype == "person"}
            self.filtered_accounts = []
            if final_acc_ids:
                self.filtered_accounts = session.exec(
                    select(Account).where(Account.id.in_(final_acc_ids))
                ).all()
            self.filtered_contacts = []
            if final_con_ids:
                self.filtered_contacts = session.exec(
                    select(Contact).where(Contact.id.in_(final_con_ids))
                ).all()
            self.filtered_relationships = [
                r
                for r in all_rels
                if (r.source_type, r.source_id) in visited
                and (r.target_type, r.target_id) in visited
            ]

    @rx.event
    def handle_search(self, query: str):
        """Update search query and reload data."""
        self.search_query = query
        yield RelationshipState.load_data

    @rx.event
    def set_node_limit(self, limit: int):
        """Update node limit and reload data."""
        self.node_limit = limit
        yield RelationshipState.load_data

    @rx.event
    def seed_database(self):
        """Seed database with Company, Person, and Multi-type Relationships."""
        try:
            with rx.session() as session:
                sqlmodel.SQLModel.metadata.create_all(session.get_bind())
                acme = Account(
                    name="Acme Corp", ticker="ACME", dynamics_account_id="ACC-001"
                )
                stark = Account(
                    name="Stark Ind", ticker="STRK", dynamics_account_id="ACC-002"
                )
                wayne = Account(
                    name="Wayne Ent", ticker="WAYN", dynamics_account_id="ACC-003"
                )
                session.add(acme)
                session.add(stark)
                session.add(wayne)
                session.flush()
                wile = Contact(
                    first_name="Wile E.",
                    last_name="Coyote",
                    job_title="Genius",
                    account_id=acme.id,
                )
                tony = Contact(
                    first_name="Tony",
                    last_name="Stark",
                    job_title="CEO",
                    account_id=stark.id,
                )
                pepper = Contact(
                    first_name="Pepper",
                    last_name="Potts",
                    job_title="CEO",
                    account_id=stark.id,
                )
                bruce = Contact(
                    first_name="Bruce",
                    last_name="Wayne",
                    job_title="Chairman",
                    account_id=wayne.id,
                )
                session.add(wile)
                session.add(tony)
                session.add(pepper)
                session.add(bruce)
                session.flush()
                rel_social = Relationship(
                    score=20,
                    relationship_type=RelationshipType.SOCIAL,
                    term=RelationshipTerm.COLLEAGUE,
                    is_directed=False,
                    source_type="person",
                    source_id=tony.id,
                    target_type="person",
                    target_id=bruce.id,
                )
                session.add(rel_social)
                rel_biz = Relationship(
                    score=-50,
                    relationship_type=RelationshipType.BUSINESS,
                    term=RelationshipTerm.COMPETITOR,
                    is_directed=False,
                    source_type="company",
                    source_id=stark.id,
                    target_type="company",
                    target_id=wayne.id,
                )
                session.add(rel_biz)
                rel_social2 = Relationship(
                    score=80,
                    relationship_type=RelationshipType.SOCIAL,
                    term=RelationshipTerm.FRIEND,
                    is_directed=False,
                    source_type="person",
                    source_id=pepper.id,
                    target_type="person",
                    target_id=tony.id,
                )
                session.add(rel_social2)
                rel_invest = Relationship(
                    score=50,
                    relationship_type=RelationshipType.BUSINESS,
                    term=RelationshipTerm.INVESTED_IN,
                    is_directed=True,
                    source_type="company",
                    source_id=wayne.id,
                    target_type="company",
                    target_id=acme.id,
                )
                session.add(rel_invest)
                session.commit()
        except Exception as e:
            logging.exception(f"Error seeding database: {e}")

    @rx.var
    def graph_data(self) -> dict:
        """Transform filtered entities and relationships into graph nodes and edges."""
        nodes = []
        edges = []
        center_x, center_y = (0, 0)
        current_accounts = self.filtered_accounts
        current_contacts = self.filtered_contacts
        current_relationships = self.filtered_relationships
        show_labels = self.zoom_level >= 0.6
        small_nodes = self.zoom_level < 0.4
        simplify_edges = self.zoom_level < 0.5
        total_nodes = len(current_accounts) + len(current_contacts)
        should_animate_particles = total_nodes <= 100
        comp_size = "50px" if small_nodes else "100px"
        pers_size = "30px" if small_nodes else "60px"

        @rx.event
        def get_id(obj):
            return getattr(obj, "id", obj.get("id") if isinstance(obj, dict) else None)

        @rx.event
        def get_attr(obj, attr, default=""):
            return getattr(
                obj, attr, obj.get(attr, default) if isinstance(obj, dict) else default
            )

        for idx, acc in enumerate(current_accounts):
            acc_id = get_id(acc)
            acc_name = get_attr(acc, "name")
            acc_ticker = get_attr(acc, "ticker")
            x = center_x + 300 * math.cos(
                2 * math.pi * idx / (len(current_accounts) or 1)
            )
            y = center_y + 300 * math.sin(
                2 * math.pi * idx / (len(current_accounts) or 1)
            )
            nodes.append(
                {
                    "id": f"acc-{acc_id}",
                    "type": "account",
                    "group": "company",
                    "data": {
                        "label": acc_name if show_labels else "",
                        "name": acc_name,
                        "display_name": acc_name,
                        "ticker": acc_ticker,
                        "job": "Company",
                        "type": "company",
                    },
                    "position": {"x": x, "y": y},
                    "style": {
                        "width": comp_size,
                        "height": comp_size,
                        "background": "#1e1b4b",
                        "color": "white",
                        "borderRadius": "8px",
                        "display": "flex",
                        "justifyContent": "center",
                        "alignItems": "center",
                        "textAlign": "center",
                        "fontWeight": "bold",
                    },
                }
            )
        for idx, con in enumerate(current_contacts):
            con_id = get_id(con)
            con_first = get_attr(con, "first_name")
            con_last = get_attr(con, "last_name")
            con_job = get_attr(con, "job_title")
            con_acc_id = get_attr(con, "account_id")
            offset_x = 400 + 100 * math.cos(
                2 * math.pi * idx / (len(current_contacts) or 1)
            )
            offset_y = 400 + 100 * math.sin(
                2 * math.pi * idx / (len(current_contacts) or 1)
            )
            nodes.append(
                {
                    "id": f"con-{con_id}",
                    "type": "contact",
                    "group": "person",
                    "data": {
                        "label": f"{con_first} {con_last}" if show_labels else "",
                        "first_name": con_first,
                        "last_name": con_last,
                        "display_name": f"{con_first} {con_last}",
                        "job": con_job,
                        "job_title": con_job,
                        "type": "person",
                    },
                    "position": {"x": offset_x, "y": offset_y},
                    "style": {
                        "width": pers_size,
                        "height": pers_size,
                        "background": "#bae6fd",
                        "color": "#0f172a",
                        "borderRadius": "50%",
                        "border": "2px solid #0284c7",
                        "display": "flex",
                        "justifyContent": "center",
                        "alignItems": "center",
                        "textAlign": "center",
                        "fontSize": "10px",
                    },
                }
            )
            acc_ids = {get_id(a) for a in current_accounts}
            if con_acc_id and con_acc_id in acc_ids:
                edges.append(
                    {
                        "id": f"emp-{con_id}-{con_acc_id}",
                        "source": f"acc-{con_acc_id}",
                        "target": f"con-{con_id}",
                        "type": "smoothstep",
                        "animated": False,
                        "style": {
                            "stroke": "#334155",
                            "strokeWidth": 2,
                            "strokeDasharray": "5,5",
                        },
                        "data": {"type": "employment", "score": 0},
                    }
                )
        for rel in current_relationships:
            if not rel.is_active and (not self.show_historic):
                continue
            src_prefix = "acc-" if rel.source_type == "company" else "con-"
            tgt_prefix = "acc-" if rel.target_type == "company" else "con-"
            src_id = f"{src_prefix}{rel.source_id}"
            tgt_id = f"{tgt_prefix}{rel.target_id}"
            is_employment = rel.relationship_type == RelationshipType.EMPLOYMENT
            edge_data = {
                "score": rel.score,
                "type": rel.relationship_type.value,
                "term": rel.term.value,
                "is_directed": rel.is_directed,
                "is_active": rel.is_active,
            }
            edge_dict = {
                "id": f"rel-{rel.id}",
                "source": src_id,
                "target": tgt_id,
                "type": "smoothstep",
                "data": edge_data,
            }
            if rel.is_directed:
                edge_dict["markerEnd"] = {"type": "arrowclosed"}
            if not rel.is_active:
                edge_dict.update(
                    {
                        "animated": False,
                        "label": f"{rel.term.value} (Deleted)",
                        "style": {
                            "stroke": "#94a3b8",
                            "strokeWidth": 1,
                            "strokeDasharray": "5,5",
                            "opacity": 0.4,
                        },
                        "labelStyle": {"fill": "#94a3b8", "fontSize": 10},
                    }
                )
            elif is_employment:
                edge_dict.update(
                    {
                        "animated": False,
                        "style": {
                            "stroke": "#334155",
                            "strokeWidth": 2,
                            "strokeDasharray": "5,5",
                        },
                    }
                )
            else:
                edge_color = self.get_edge_color(rel.score)
                if simplify_edges:
                    edge_dict.update(
                        {
                            "animated": should_animate_particles,
                            "style": {
                                "stroke": edge_color,
                                "strokeWidth": 1,
                                "strokeDasharray": "0",
                            },
                        }
                    )
                else:
                    edge_dict.update(
                        {
                            "label": f"{rel.relationship_type.value.title()} ({rel.score})",
                            "animated": should_animate_particles,
                            "style": {
                                "stroke": edge_color,
                                "strokeWidth": 3,
                                "strokeDasharray": "0",
                            },
                            "labelStyle": {
                                "fill": edge_color,
                                "fontWeight": 700,
                                "fontSize": 11,
                            },
                            "labelShowBg": True,
                            "labelBgStyle": {
                                "fill": "#ffffff",
                                "fillOpacity": 0.95,
                                "stroke": edge_color,
                                "strokeWidth": 1,
                            },
                            "labelBgPadding": [8, 4],
                            "labelBgBorderRadius": 6,
                        }
                    )
            edges.append(edge_dict)
        return {"nodes": nodes, "edges": edges}

    @rx.event
    def get_edge_color(self, score: int) -> str:
        """Return gradient color based on relationship score."""

        @rx.event
        def interpolate(start_rgb, end_rgb, factor):
            r = int(start_rgb[0] + (end_rgb[0] - start_rgb[0]) * factor)
            g = int(start_rgb[1] + (end_rgb[1] - start_rgb[1]) * factor)
            b = int(start_rgb[2] + (end_rgb[2] - start_rgb[2]) * factor)
            return f"#{r:02x}{g:02x}{b:02x}"

        score = max(-100, min(100, score))
        red_rgb = (239, 68, 68)
        gray_rgb = (156, 163, 175)
        green_rgb = (16, 185, 129)
        if score < 0:
            factor = (score + 100) / 100.0
            return interpolate(red_rgb, gray_rgb, factor)
        else:
            factor = score / 100.0
            return interpolate(gray_rgb, green_rgb, factor)

    @rx.event
    def on_node_click(self, node: dict):
        """Handle node click to show details."""
        if isinstance(node, dict):
            self.selected_node_id = node.get("id", "")
        else:
            self.selected_node_id = getattr(node, "id", "")
        try:
            parts = self.selected_node_id.split("-")
            if len(parts) >= 2:
                prefix, id_str = (parts[0], parts[1])
                node_id = int(id_str)
                node_type = "company" if prefix == "acc" else "person"
                with rx.session() as session:
                    if node_type == "company":
                        obj = session.get(Account, node_id)
                        if obj:
                            self.selected_node_data = {
                                "id": str(node_id),
                                "display_name": obj.name,
                                "job": "Company",
                                "type": "company",
                                "updated_at": obj.updated_at.strftime(
                                    "%Y-%m-%d %H:%M:%S"
                                ),
                                "last_modified_by": obj.last_modified_by,
                                "operation_type": "UPDATE",
                            }
                    else:
                        obj = session.get(Contact, node_id)
                        if obj:
                            self.selected_node_data = {
                                "id": str(node_id),
                                "display_name": f"{obj.first_name} {obj.last_name}",
                                "job": obj.job_title,
                                "type": "person",
                                "updated_at": obj.updated_at.strftime(
                                    "%Y-%m-%d %H:%M:%S"
                                ),
                                "last_modified_by": obj.last_modified_by,
                                "operation_type": "UPDATE",
                            }
        except Exception as e:
            logging.exception(f"Error loading node details: {e}")
            self.selected_node_data = {}
        self.edit_mode = "node"
        self.node_create_mode = False
        self.show_side_panel = True
        yield RelationshipState.load_active_node_relationships

    @rx.event
    def on_edge_click(self, edge: dict):
        """Handle edge click to show score editor."""
        if isinstance(edge, dict):
            edge_id = edge.get("id", "")
            data = edge.get("data", {}) or {}
        else:
            edge_id = getattr(edge, "id", "")
            data = getattr(edge, "data", None) or {}
        self.selected_edge_id = edge_id
        if isinstance(data, dict):
            self.editing_score = int(data.get("score", 0))
            self.editing_relationship_type = str(data.get("type", "employment"))
            self.editing_term = str(data.get("term", "works_for"))
            self.editing_is_directed = bool(data.get("is_directed", True))
        else:
            self.editing_score = int(getattr(data, "score", 0))
            self.editing_relationship_type = str(getattr(data, "type", "employment"))
            self.editing_term = str(getattr(data, "term", "works_for"))
            self.editing_is_directed = bool(getattr(data, "is_directed", True))
        self.node_create_mode = False
        if edge_id.startswith("rel-"):
            self.edit_mode = "edge"
            self.show_side_panel = True
        elif edge_id.startswith("emp-"):
            self.edit_mode = "edge"
            self.editing_relationship_type = "employment"
            self.editing_term = "works_for"
            self.editing_is_directed = True
            self.show_side_panel = True
        else:
            self.edit_mode = "none"
            self.show_side_panel = False

    @rx.event
    def close_panel(self):
        """Close the side panel."""
        self.show_side_panel = False
        self.edit_mode = "none"
        self.node_create_mode = False

    @rx.event
    def set_editing_score(self, value: int):
        """Update the temporary score value while editing."""
        self.editing_score = value

    @rx.event
    def save_relationship_update(self):
        """Commit the score change to the database."""
        try:
            if self.selected_edge_id.startswith("rel-"):
                rel_id = int(self.selected_edge_id.split("-")[1])
                self.update_relationship_score(rel_id, self.editing_score)
        except Exception as e:
            logging.exception(f"Failed to save relationship: {e}")

    @rx.event
    def save_node(self):
        """Consolidated handler for creating or updating a node with audit trail."""
        self.is_loading = True
        yield
        try:
            timestamp = datetime.now()
            self.last_operation_timestamp = timestamp.strftime("%Y-%m-%d %H:%M:%S")
            with rx.session() as session:
                if self.node_create_mode:
                    self.last_operation_type = "CREATE"
                    if self.new_node_type == "person":
                        if not self.new_node_name.strip():
                            rx.toast("First name is required", duration=3000)
                            return
                        existing = session.exec(
                            select(Contact).where(
                                col(Contact.first_name).ilike(self.new_node_name),
                                col(Contact.last_name).ilike(self.new_node_last_name),
                            )
                        ).first()
                        if existing:
                            rx.toast(f"Contact already exists", duration=3000)
                            return
                        new_node = Contact(
                            first_name=self.new_node_name,
                            last_name=self.new_node_last_name,
                            job_title=self.new_node_title_or_ticker,
                            created_at=timestamp,
                            updated_at=timestamp,
                            last_modified_by=self.current_user,
                        )
                        session.add(new_node)
                        session.commit()
                        rx.toast(f"Created Person: {self.new_node_name}", duration=3000)
                    else:
                        if not self.new_node_name.strip():
                            rx.toast("Company name is required", duration=3000)
                            return
                        existing = session.exec(
                            select(Account).where(
                                col(Account.name).ilike(self.new_node_name)
                            )
                        ).first()
                        if existing:
                            rx.toast(f"Company already exists", duration=3000)
                            return
                        new_node = Account(
                            name=self.new_node_name,
                            ticker=self.new_node_title_or_ticker,
                            created_at=timestamp,
                            updated_at=timestamp,
                            last_modified_by=self.current_user,
                        )
                        session.add(new_node)
                        session.commit()
                        rx.toast(
                            f"Created Company: {self.new_node_name}", duration=3000
                        )
                    self.node_create_mode = False
                    self.show_side_panel = False
                elif self.edit_mode == "node" and self.editing_node_id:
                    self.last_operation_type = "UPDATE"
                    if self.editing_node_type == "company":
                        node = session.get(Account, self.editing_node_id)
                        if node:
                            if "name" in self.editing_node_data:
                                node.name = self.editing_node_data["name"]
                            if "ticker" in self.editing_node_data:
                                node.ticker = self.editing_node_data["ticker"]
                            node.updated_at = timestamp
                            node.last_modified_by = self.current_user
                            session.add(node)
                    else:
                        node = session.get(Contact, self.editing_node_id)
                        if node:
                            if "first_name" in self.editing_node_data:
                                node.first_name = self.editing_node_data["first_name"]
                            if "last_name" in self.editing_node_data:
                                node.last_name = self.editing_node_data["last_name"]
                            if "job_title" in self.editing_node_data:
                                node.job_title = self.editing_node_data["job_title"]
                            node.updated_at = timestamp
                            node.last_modified_by = self.current_user
                            session.add(node)
                    session.commit()
                    rx.toast("Node updated successfully", duration=3000)
                    self.is_editing = False
                    yield RelationshipState.on_node_click(node)
            yield RelationshipState.load_data
        except Exception as e:
            logging.exception(f"Error in save_node: {e}")
            rx.toast(f"Failed to save: {str(e)}", duration=3000)
        finally:
            self.is_loading = False

    @rx.event
    def update_relationship_score(self, rel_id: int, new_score: int):
        """Update the relationship score."""
        try:
            with rx.session() as session:
                relationship = session.get(Relationship, rel_id)
                if relationship:
                    previous_score = relationship.score
                    relationship.score = new_score
                    relationship.last_updated = datetime.now()
                    relationship.last_modified_by = self.current_user
                    session.add(relationship)
                    log_entry = RelationshipLog(
                        relationship_id=relationship.id,
                        previous_score=previous_score,
                        new_score=new_score,
                        changed_at=datetime.now(),
                        note="Manual update via graph",
                        action="score_change",
                    )
                    session.add(log_entry)
                    session.commit()
            yield RelationshipState.load_data
        except Exception as e:
            logging.exception(f"Error updating score: {e}")

    @rx.event
    def create_relationship_with_term(
        self,
        session,
        source_type: str,
        source_id: int,
        target_type: str,
        target_id: int,
        term: RelationshipTerm,
        rel_type: RelationshipType,
    ):
        """Helper to create a relationship with defaults based on term."""
        defaults = TERM_DEFAULTS.get(term, {"is_directed": False, "default_score": 0})
        new_rel = Relationship(
            score=defaults["default_score"],
            relationship_type=rel_type,
            term=term,
            is_directed=defaults["is_directed"],
            is_active=True,
            source_type=source_type,
            source_id=source_id,
            target_type=target_type,
            target_id=target_id,
        )
        session.add(new_rel)
        return new_rel

    @rx.event
    def soft_delete_relationship(self, rel_id: int):
        """Soft delete a relationship."""
        try:
            with rx.session() as session:
                relationship = session.get(Relationship, rel_id)
                if relationship:
                    relationship.is_active = False
                    relationship.last_updated = datetime.now()
                    session.add(relationship)
                    log_entry = RelationshipLog(
                        relationship_id=relationship.id,
                        previous_score=relationship.score,
                        new_score=0,
                        action="soft_delete",
                        changed_at=datetime.now(),
                        note="Relationship soft deleted",
                    )
                    session.add(log_entry)
                    session.commit()
            self.close_panel()
            yield RelationshipState.load_data
            return rx.toast("Relationship deleted", duration=3000)
        except Exception as e:
            logging.exception(f"Error deleting relationship: {e}")
            return rx.toast("Failed to delete relationship", duration=3000)

    @rx.event
    def update_relationship_term(self, rel_id: int, new_term: str):
        """Update the relationship term and apply defaults."""
        try:
            term_enum = RelationshipTerm(new_term)
            defaults = TERM_DEFAULTS.get(
                term_enum, {"is_directed": False, "default_score": 0}
            )
            new_type = TERM_TO_TYPE.get(term_enum, RelationshipType.SOCIAL)
            with rx.session() as session:
                relationship = session.get(Relationship, rel_id)
                if relationship:
                    previous_term = relationship.term
                    previous_score = relationship.score
                    relationship.term = term_enum
                    relationship.relationship_type = new_type
                    relationship.is_directed = defaults["is_directed"]
                    relationship.score = defaults["default_score"]
                    relationship.last_updated = datetime.now()
                    relationship.last_modified_by = self.current_user
                    session.add(relationship)
                    log_entry = RelationshipLog(
                        relationship_id=relationship.id,
                        previous_score=previous_score,
                        new_score=relationship.score,
                        previous_term=previous_term,
                        new_term=new_term,
                        action="term_change",
                        changed_at=datetime.now(),
                        note=f"Term changed to {new_term}",
                    )
                    session.add(log_entry)
                    session.commit()
                    self.editing_relationship_type = new_type.value
                    self.editing_term = new_term
                    self.editing_is_directed = defaults["is_directed"]
                    self.editing_score = defaults["default_score"]
            yield RelationshipState.load_data
            return rx.toast(f"Updated relationship to {new_term}", duration=3000)
        except Exception as e:
            logging.exception(f"Error updating term: {e}")
            return rx.toast("Failed to update term", duration=3000)

    @rx.event
    def on_connect(self, connection: dict):
        """Handle creating new relationships by dragging between nodes."""
        if isinstance(connection, dict):
            source = connection.get("source", "")
            target = connection.get("target", "")
        else:
            source = getattr(connection, "source", "")
            target = getattr(connection, "target", "")
        try:
            src_parts = source.split("-")
            tgt_parts = target.split("-")
            if len(src_parts) < 2 or len(tgt_parts) < 2:
                return rx.toast("Invalid node identifiers", duration=3000)
            src_prefix, src_id_str = (src_parts[0], src_parts[1])
            tgt_prefix, tgt_id_str = (tgt_parts[0], tgt_parts[1])
            src_id = int(src_id_str)
            tgt_id = int(tgt_id_str)
            src_type = "company" if src_prefix == "acc" else "person"
            tgt_type = "company" if tgt_prefix == "acc" else "person"
            if src_type == tgt_type and src_id == tgt_id:
                return rx.toast("Cannot connect a node to itself", duration=3000)
            rel_type = RelationshipType.SOCIAL
            default_term = RelationshipTerm.FRIEND
            if src_type == "company" and tgt_type == "company":
                rel_type = RelationshipType.BUSINESS
                default_term = RelationshipTerm.COMPETITOR
            elif (
                src_type == "person"
                and tgt_type == "company"
                or (src_type == "company" and tgt_type == "person")
            ):
                rel_type = RelationshipType.EMPLOYMENT
                default_term = RelationshipTerm.WORKS_FOR
            elif src_type == "person" and tgt_type == "person":
                rel_type = RelationshipType.SOCIAL
                default_term = RelationshipTerm.FRIEND
            new_rel_id = None
            new_rel_score = 0
            new_rel_type_val = ""
            new_rel_term_val = ""
            new_rel_is_directed = False
            operation_success = False
            success_message = ""
            with rx.session() as session:
                existing = session.exec(
                    sqlmodel.select(Relationship).where(
                        Relationship.source_type == src_type,
                        Relationship.source_id == src_id,
                        Relationship.target_type == tgt_type,
                        Relationship.target_id == tgt_id,
                    )
                ).first()
                if existing:
                    if not existing.is_active:
                        existing.is_active = True
                        existing.last_updated = datetime.now()
                        session.add(existing)
                        log_entry = RelationshipLog(
                            relationship_id=existing.id,
                            previous_score=existing.score,
                            new_score=existing.score,
                            action="reactivate",
                            changed_at=datetime.now(),
                            note="Reactivated via graph connection",
                        )
                        session.add(log_entry)
                        session.commit()
                        session.refresh(existing)
                        new_rel_id = existing.id
                        new_rel_score = existing.score
                        new_rel_type_val = existing.relationship_type.value
                        new_rel_term_val = existing.term.value
                        new_rel_is_directed = existing.is_directed
                        operation_success = True
                        success_message = "Reactivated existing relationship"
                    else:
                        return rx.toast("Relationship already exists", duration=3000)
                else:
                    new_rel = self.create_relationship_with_term(
                        session,
                        src_type,
                        src_id,
                        tgt_type,
                        tgt_id,
                        default_term,
                        rel_type,
                    )
                    session.commit()
                    session.refresh(new_rel)
                    new_rel_id = new_rel.id
                    new_rel_score = new_rel.score
                    new_rel_type_val = new_rel.relationship_type.value
                    new_rel_term_val = new_rel.term.value
                    new_rel_is_directed = new_rel.is_directed
                    operation_success = True
                    success_message = f"Created new {rel_type.value} relationship"
            if operation_success:
                rx.toast(success_message, duration=3000)
                self.selected_edge_id = f"rel-{new_rel_id}"
                self.editing_score = new_rel_score
                self.editing_relationship_type = new_rel_type_val
                self.editing_term = new_rel_term_val
                self.editing_is_directed = new_rel_is_directed
                self.edit_mode = "edge"
                self.show_side_panel = True
                yield RelationshipState.load_data
        except Exception as e:
            logging.exception(f"Failed to link nodes: {e}")
            return rx.toast("Failed to create relationship", duration=3000)

    @rx.event
    def validate_node_data(self, node_type: str, data: dict) -> tuple[bool, str]:
        """Validate node data before creation or update."""
        if node_type == "company":
            name = data.get("name", "")
            if not name or not str(name).strip():
                return (False, "Company name is required")
        elif node_type == "person":
            if "name" in data:
                name = data.get("name", "")
                if not name or not str(name).strip():
                    return (False, "Name is required")
            if "first_name" in data:
                if not data.get("first_name", "").strip():
                    return (False, "First name is required")
        return (True, "")

    @rx.event
    def add_node(
        self,
        node_type: str,
        name: str,
        title_or_ticker: str,
        additional_data: dict = None,
    ):
        """Create new Account or Contact."""
        if additional_data is None:
            additional_data = {}
        is_valid, error_msg = self.validate_node_data(
            node_type, {"name": name, "title_or_ticker": title_or_ticker}
        )
        if not is_valid:
            return rx.toast(error_msg, duration=3000)
        try:
            with rx.session() as session:
                if node_type == "company":
                    existing = session.exec(
                        select(Account).where(col(Account.name).ilike(name))
                    ).first()
                    if existing:
                        return rx.toast(
                            f"Company '{name}' already exists", duration=3000
                        )
                    new_account = Account(
                        name=name, ticker=title_or_ticker, **additional_data
                    )
                    session.add(new_account)
                    session.commit()
                    session.refresh(new_account)
                    node_id = new_account.id
                elif node_type == "person":
                    parts = name.strip().split(" ", 1)
                    first_name = parts[0]
                    last_name = parts[1] if len(parts) > 1 else ""
                    existing = session.exec(
                        select(Contact).where(
                            col(Contact.first_name).ilike(first_name),
                            col(Contact.last_name).ilike(last_name),
                        )
                    ).first()
                    if existing:
                        return rx.toast(
                            f"Contact '{first_name} {last_name}' already exists",
                            duration=3000,
                        )
                    new_contact = Contact(
                        first_name=first_name,
                        last_name=last_name,
                        job_title=title_or_ticker,
                        **additional_data,
                    )
                    session.add(new_contact)
                    session.commit()
                    session.refresh(new_contact)
                    node_id = new_contact.id
                else:
                    return rx.toast("Invalid node type", duration=3000)
            yield RelationshipState.load_data
            return rx.toast(f"Created {node_type} successfully", duration=3000)
        except Exception as e:
            logging.exception(f"Error adding node: {e}")
            return rx.toast("Failed to add node", duration=3000)

    @rx.event
    def update_node(self, node_id: int, node_type: str, updated_data: dict):
        """Update existing node data."""
        try:
            with rx.session() as session:
                if node_type == "company":
                    account = session.get(Account, node_id)
                    if not account:
                        return rx.toast("Account not found", duration=3000)
                    if "name" in updated_data and updated_data["name"]:
                        account.name = updated_data["name"]
                    if "ticker" in updated_data:
                        account.ticker = updated_data["ticker"]
                    session.add(account)
                elif node_type == "person":
                    contact = session.get(Contact, node_id)
                    if not contact:
                        return rx.toast("Contact not found", duration=3000)
                    if "first_name" in updated_data and updated_data["first_name"]:
                        contact.first_name = updated_data["first_name"]
                    if "last_name" in updated_data:
                        contact.last_name = updated_data["last_name"]
                    if "job_title" in updated_data:
                        contact.job_title = updated_data["job_title"]
                    session.add(contact)
                session.commit()
            yield RelationshipState.load_data
            return rx.toast("Node updated successfully", duration=3000)
        except Exception as e:
            logging.exception(f"Error updating node: {e}")
            return rx.toast("Failed to update node", duration=3000)

    @rx.event
    def delete_node(self, node_id: int, node_type: str):
        """Hard delete node and cascade delete relationships."""
        try:
            with rx.session() as session:
                rels_to_delete = session.exec(
                    select(Relationship).where(
                        or_(
                            (Relationship.source_type == node_type)
                            & (Relationship.source_id == node_id),
                            (Relationship.target_type == node_type)
                            & (Relationship.target_id == node_id),
                        )
                    )
                ).all()
                deleted_count = len(rels_to_delete)
                for rel in rels_to_delete:
                    logging.info(
                        f"Deleting relationship {rel.id} due to node {node_id} deletion"
                    )
                    session.exec(
                        delete(RelationshipLog).where(
                            RelationshipLog.relationship_id == rel.id
                        )
                    )
                    session.delete(rel)
                if node_type == "company":
                    account = session.get(Account, node_id)
                    if account:
                        linked_contacts = session.exec(
                            select(Contact).where(Contact.account_id == node_id)
                        ).all()
                        for c in linked_contacts:
                            c.account_id = None
                            session.add(c)
                        session.delete(account)
                elif node_type == "person":
                    contact = session.get(Contact, node_id)
                    if contact:
                        session.delete(contact)
                session.commit()
            self.close_panel()
            yield RelationshipState.load_data
            return rx.toast(
                f"Deleted node and {deleted_count} relationships", duration=3000
            )
        except Exception as e:
            logging.exception(f"Error deleting node: {e}")
            return rx.toast("Failed to delete node", duration=3000)

    @rx.event
    def load_active_node_relationships(self):
        """Load relationships for the currently selected node into state."""
        if not self.selected_node_id:
            return
        try:
            parts = self.selected_node_id.split("-")
            if len(parts) < 2:
                return
            prefix, id_str = (parts[0], parts[1])
            node_id = int(id_str)
            node_type = "company" if prefix == "acc" else "person"
            rels = self.get_node_relationships(node_id, node_type)
            for r in rels:
                score = r.get("score", 0)
                if score <= -30:
                    r["badge_class"] = "bg-red-50 text-red-700 border-red-200"
                elif score >= 30:
                    r["badge_class"] = "bg-green-50 text-green-700 border-green-200"
                else:
                    r["badge_class"] = "bg-gray-50 text-gray-700 border-gray-200"
            self.active_node_relationships = rels
        except Exception as e:
            logging.exception(f"Error loading active node relationships: {e}")

    @rx.event
    def get_node_relationships(self, node_id: int, node_type: str) -> list[dict]:
        """Fetch active relationships for a node."""
        try:
            relationships_data = []
            with rx.session() as session:
                rels = session.exec(
                    select(Relationship)
                    .where(
                        (Relationship.is_active == True)
                        & or_(
                            (Relationship.source_type == node_type)
                            & (Relationship.source_id == node_id),
                            (Relationship.target_type == node_type)
                            & (Relationship.target_id == node_id),
                        )
                    )
                    .order_by(col(Relationship.score).desc())
                ).all()
                for rel in rels:
                    is_source = (
                        rel.source_type == node_type and rel.source_id == node_id
                    )
                    conn_type = rel.target_type if is_source else rel.source_type
                    conn_id = rel.target_id if is_source else rel.source_id
                    conn_name = "Unknown"
                    if conn_type == "company":
                        acc = session.get(Account, conn_id)
                        if acc:
                            conn_name = acc.name
                    elif conn_type == "person":
                        cont = session.get(Contact, conn_id)
                        if cont:
                            conn_name = f"{cont.first_name} {cont.last_name}"
                    relationships_data.append(
                        {
                            "relationship_id": rel.id,
                            "score": rel.score,
                            "term": rel.term.value,
                            "is_directed": rel.is_directed,
                            "connected_node_id": conn_id,
                            "connected_node_type": conn_type,
                            "connected_node_name": conn_name,
                            "type": rel.relationship_type.value,
                        }
                    )
            return relationships_data
        except Exception as e:
            logging.exception(f"Error fetching node relationships: {e}")
            return []

    @rx.event
    def get_all_nodes_for_search(self) -> list[dict]:
        """Fetch all nodes formatted for search selection."""
        nodes = []
        try:
            with rx.session() as session:
                accounts = session.exec(select(Account)).all()
                for acc in accounts:
                    nodes.append(
                        {
                            "id": acc.id,
                            "type": "company",
                            "name": acc.name,
                            "subtitle": acc.ticker,
                            "full_id": f"acc-{acc.id}",
                        }
                    )
                contacts = session.exec(select(Contact)).all()
                for con in contacts:
                    nodes.append(
                        {
                            "id": con.id,
                            "type": "person",
                            "name": f"{con.first_name} {con.last_name}",
                            "subtitle": con.job_title,
                            "full_id": f"con-{con.id}",
                        }
                    )
        except Exception as e:
            logging.exception(f"Error fetching nodes for search: {e}")
        return nodes

    @rx.event
    def filter_target_nodes(self, query: str):
        """Filter nodes for relationship creation target selection."""
        self.relationship_target_search = query
        all_nodes = self.get_all_nodes_for_search()
        current_node_full_id = self.selected_node_id
        filtered = []
        query = query.lower()
        for node in all_nodes:
            if node["full_id"] == current_node_full_id:
                continue
            if query in node["name"].lower() or query in node["subtitle"].lower():
                filtered.append(node)
        self.filtered_target_nodes = filtered[:10]

    @rx.event
    def prepare_node_edit(self):
        """Prepare state for editing the currently selected node."""
        if not self.selected_node_id:
            return
        try:
            parts = self.selected_node_id.split("-")
            if len(parts) < 2:
                return
            prefix, id_str = (parts[0], parts[1])
            node_id = int(id_str)
            node_type = "company" if prefix == "acc" else "person"
            self.is_editing = True
            self.editing_node_id = node_id
            self.editing_node_type = node_type
            with rx.session() as session:
                if node_type == "company":
                    acc = session.get(Account, node_id)
                    if acc:
                        self.editing_node_data = {
                            "name": acc.name,
                            "ticker": acc.ticker,
                            "first_name": "",
                            "last_name": "",
                            "job_title": "",
                        }
                else:
                    con = session.get(Contact, node_id)
                    if con:
                        self.editing_node_data = {
                            "first_name": con.first_name,
                            "last_name": con.last_name,
                            "job_title": con.job_title,
                            "name": f"{con.first_name} {con.last_name}",
                            "ticker": "",
                        }
        except Exception as e:
            logging.exception(f"Error preparing node edit: {e}")
            rx.toast("Error preparing edit mode", duration=3000)

    @rx.event
    def cancel_edit(self):
        """Cancel edit mode and reset temporary state."""
        self.is_editing = False
        self.is_creating_relationship = False
        self.editing_node_data = {}
        self.relationship_target_search = ""
        self.filtered_target_nodes = []

    @rx.event
    def start_relationship_creation(self):
        """Enter relationship creation mode."""
        self.is_creating_relationship = True
        self.relationship_target_search = ""
        self.creation_target_id = 0
        self.creation_target_name = ""
        self.creation_target_type = ""
        self.creation_term = "friend"
        self.creation_score = 0
        self.filter_target_nodes("")

    @rx.event
    def set_creation_target(self, id: int, type: str, name: str):
        """Set the target node for the new relationship."""
        self.creation_target_id = id
        self.creation_target_type = type
        self.creation_target_name = name

    @rx.event
    def set_creation_term(self, term: str):
        """Set the term for new relationship and update score defaults."""
        self.creation_term = term
        try:
            term_enum = RelationshipTerm(term)
            defaults = TERM_DEFAULTS.get(term_enum, {"default_score": 0})
            self.creation_score = defaults["default_score"]
        except ValueError as e:
            logging.exception(f"Error setting creation term: {e}")

    @rx.event
    def set_creation_score(self, score: int):
        """Set the score for new relationship."""
        self.creation_score = score

    @rx.event
    def cancel_relationship_creation(self):
        """Cancel relationship creation mode."""
        self.is_creating_relationship = False
        self.creation_target_id = 0
        self.creation_target_name = ""

    @rx.event
    def create_relationship_from_panel(self):
        """Create a relationship from the side panel UI."""
        if not self.selected_node_id:
            return rx.toast("No source node selected", duration=3000)
        if not self.creation_target_id:
            return rx.toast("Please select a target node", duration=3000)
        target_node_id = self.creation_target_id
        target_node_type = self.creation_target_type
        term = self.creation_term
        score = self.creation_score
        try:
            parts = self.selected_node_id.split("-")
            src_prefix, src_id_str = (parts[0], parts[1])
            source_id = int(src_id_str)
            source_type = "company" if src_prefix == "acc" else "person"
            term_enum = RelationshipTerm(term)
            rel_type = TERM_TO_TYPE.get(term_enum, RelationshipType.SOCIAL)
            with rx.session() as session:
                existing = session.exec(
                    select(Relationship).where(
                        Relationship.source_type == source_type,
                        Relationship.source_id == source_id,
                        Relationship.target_type == target_node_type,
                        Relationship.target_id == target_node_id,
                    )
                ).first()
                if existing:
                    if not existing.is_active:
                        existing.is_active = True
                        existing.term = term_enum
                        existing.relationship_type = rel_type
                        existing.score = score
                        existing.last_updated = datetime.now()
                        session.add(existing)
                        log_entry = RelationshipLog(
                            relationship_id=existing.id,
                            previous_score=existing.score,
                            new_score=score,
                            action="reactivate_panel",
                            changed_at=datetime.now(),
                            note="Reactivated via side panel",
                        )
                        session.add(log_entry)
                        session.commit()
                        rx.toast("Reactivated existing relationship", duration=3000)
                    else:
                        return rx.toast("Relationship already exists", duration=3000)
                else:
                    defaults = TERM_DEFAULTS.get(
                        term_enum, {"is_directed": False, "default_score": 0}
                    )
                    new_rel = Relationship(
                        score=score,
                        relationship_type=rel_type,
                        term=term_enum,
                        is_directed=defaults["is_directed"],
                        is_active=True,
                        source_type=source_type,
                        source_id=source_id,
                        target_type=target_node_type,
                        target_id=target_node_id,
                    )
                    session.add(new_rel)
                    session.commit()
                    rx.toast("Relationship created", duration=3000)
            self.is_creating_relationship = False
            yield RelationshipState.load_data
            yield RelationshipState.load_active_node_relationships
        except Exception as e:
            logging.exception(f"Error creating relationship from panel: {e}")
            rx.toast("Failed to create relationship", duration=3000)

    @rx.event
    def start_node_creation(self):
        """Enter node creation mode."""
        logging.info("Starting node creation mode")
        self.node_create_mode = True
        self.new_node_type = "person"
        self.new_node_name = ""
        self.new_node_last_name = ""
        self.new_node_title_or_ticker = ""
        self.show_side_panel = True
        self.edit_mode = "none"

    @rx.event
    def cancel_node_creation(self):
        """Exit node creation mode."""
        self.node_create_mode = False
        self.new_node_name = ""
        self.new_node_last_name = ""
        self.new_node_title_or_ticker = ""

    @rx.event
    def delete_current_selection(self):
        """Delete the currently selected node or relationship."""
        if self.edit_mode == "node" and self.selected_node_id:
            try:
                parts = self.selected_node_id.split("-")
                if len(parts) >= 2:
                    prefix, id_str = (parts[0], parts[1])
                    node_type = "company" if prefix == "acc" else "person"
                    return RelationshipState.delete_node(int(id_str), node_type)
            except Exception as e:
                logging.exception(f"Error parsing node deletion: {e}")
        elif self.edit_mode == "edge" and self.selected_edge_id:
            try:
                if self.selected_edge_id.startswith("rel-"):
                    rel_id = int(self.selected_edge_id.split("-")[1])
                    return RelationshipState.soft_delete_relationship(rel_id)
            except Exception as e:
                logging.exception(f"Error parsing edge deletion: {e}")
        return rx.toast("Nothing selected to delete", duration=3000)

    @rx.event
    def submit_node_creation(self):
        """Submit new node creation."""
        return RelationshipState.save_node