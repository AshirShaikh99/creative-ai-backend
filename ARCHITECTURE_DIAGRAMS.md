# Software Architecture Diagram Generator

This feature allows you to generate comprehensive software architecture diagrams for various architectural patterns and styles using natural language prompts.

## Features

- Generate visual diagrams for various software architecture patterns
- Support for microservices, event-driven, serverless, and other modern architectures
- Consistent styling and representation of common components
- Interactive diagram output with component details
- JSON representation for further customization

## Supported Architecture Patterns

The system can generate diagrams for a wide range of architectural patterns, including:

- Microservice architectures
- Event-driven architectures
- Serverless architectures
- Layered architectures
- API Gateway patterns
- CQRS (Command Query Responsibility Segregation)
- Message-based architectures
- Cloud-native architectures
- Data pipeline architectures
- And many more...

## Example Prompts

Here are some examples of prompts you can use:

1. **Microservice Architecture:**

   ```
   Create a software architecture diagram for a microservice-based e-commerce platform with user service, product catalog, order management, and payment processing.
   ```

2. **Event-Driven Architecture:**

   ```
   Design an event-driven architecture for a real-time analytics system with producers, event bus, consumers, and data processing pipelines.
   ```

3. **API Gateway Pattern:**

   ```
   Create a software architecture diagram showing API Gateway pattern with authentication, rate limiting, and service routing.
   ```

4. **CQRS Architecture:**

   ```
   Design a software architecture following the CQRS (Command Query Responsibility Segregation) pattern with separate read and write models.
   ```

5. **Serverless Architecture:**

   ```
   Create a serverless architecture diagram for a photo processing application with cloud functions, object storage, and managed database.
   ```

6. **Message Queue Architecture:**
   ```
   Design a system architecture with message queues for an order processing system handling high volume of transactions.
   ```

## Component Types

The system recognizes and properly styles various component types, including:

- User interfaces (Web, Mobile)
- API Gateways
- Microservices
- Databases (SQL, NoSQL)
- Message Queues
- Caches
- Load Balancers
- Authentication Services
- External/Third-party Services
- Serverless Functions
- Worker/Processing Agents

## Connection Types

Various types of connections between components are supported:

- Synchronous API calls
- Asynchronous events/messages
- Data flows
- Responses
- Dependencies

## Styling

Components are automatically styled based on their type for better visualization:

- UI components: Light blue
- Databases: Purple
- Services: Light gray
- Message queues: Yellow
- Caching: Green
- Authentication: Red
- External services: Dashed outline

## Using the Test Script

A test script (`test_architecture_diagrams.py`) is included to help you test various diagram generation capabilities:

```bash
python test_architecture_diagrams.py
```

This will generate diagram files in a timestamped directory and provide links to view them.

## API Usage

To generate a diagram via the API:

```javascript
const response = await fetch("/api/v1/diagram", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "user-id": "your-user-id",
  },
  body: JSON.stringify({
    message: "Create a microservice architecture for an e-commerce platform",
    options: {},
  }),
});

const result = await response.json();
```

The response includes:

- `syntax`: Mermaid diagram syntax
- `diagram_type`: Type of diagram (e.g., "software_architecture")
- `description`: Brief description of the diagram
- `nodes`: Component nodes
- `connections`: Relationships between components
- `clusters`: Groupings of related components
