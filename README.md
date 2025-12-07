# Relationship Management Dashboard

Investment Manager Relationship Management Dashboard with Microsoft Dynamics 365 integration.

## Features

- **Interactive Network Graph**: Visualize relationships between companies and people
- **Full CRUD Operations**: Create, read, update, and delete entities and relationships
- **Relationship Scoring**: Track sentiment from -100 (hostile) to +100 (friendly)
- **Audit Trail**: Complete history of all changes with timestamps
- **Search & Filter**: Find entities and build subgraphs
- **Multiple Relationship Types**: Employment, social, and business relationships

## Tech Stack

- **Reflex**: Full-stack Python framework
- **Reflex Enterprise**: Advanced flow/graph components
- **SQLModel**: Database ORM
- **Tailwind CSS**: Modern styling

## Installation

bash
pip install -r requirements.txt
reflex init
reflex run


## Database Models

- **Account**: Companies with name, ticker, Dynamics ID
- **Contact**: People with name, job title, account association
- **Relationship**: Links between entities with scores and terms
- **RelationshipLog**: Audit trail of all relationship changes

## Usage

1. **View the Graph**: Interactive network visualization with drag-and-drop
2. **Add Entities**: Click "Node" button to create new person or company
3. **Add Relationships**: Select a node, click "Link", search for target, set term/score
4. **Edit**: Click any node/edge to view details and edit
5. **Search**: Use search bar to find entities and build focused subgraphs
6. **History Toggle**: View deleted relationships in gray

## Relationship Terms

- **works_for**: Employment relationship (structural, no score)
- **invested_in**: Investment/business relationship (default +50)
- **competitor**: Competitive relationship (default -50)
- **colleague**: Professional peer (default +20)
- **friend**: Personal friendship (default +80)
- **enemy**: Antagonistic relationship (default -100)

## License

MIT
