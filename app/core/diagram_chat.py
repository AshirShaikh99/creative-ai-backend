from typing import Dict, Optional, List, Union, Any
from app.models.model import Message, ChatSession, DiagramResponse
from uuid import UUID
from groq import AsyncGroq
from app.config.config import get_settings
from app.service.qdrant_service import QdrantService
from functools import lru_cache
import hashlib
from enum import Enum
import json
import logging
import traceback
import re

logger = logging.getLogger(__name__)

class DiagramType(Enum):
    FLOWCHART = "flowchart"
    SEQUENCE = "sequenceDiagram"
    STATE = "stateDiagram-v2"
    CLASS = "classDiagram"
    ER = "erDiagram"
    GANTT = "gantt"
    MINDMAP = "mindmap"
    AI_ARCHITECTURE = "ai_architecture"
    SOFTWARE_ARCHITECTURE = "software_architecture"

class DiagramChatbot:
    def __init__(self):
        self.sessions: Dict[UUID, ChatSession] = {}
        settings = get_settings()
        self.groq_client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        self.qdrant_client = QdrantService.get_instance()
        
        # System prompts for different diagram types
        self.diagram_prompts = {
            DiagramType.FLOWCHART: "Generate a Mermaid flowchart diagram syntax.",
            DiagramType.SEQUENCE: "Create a Mermaid sequence diagram syntax.",
            DiagramType.STATE: "Design a Mermaid state diagram syntax.",
            DiagramType.CLASS: "Create a Mermaid class diagram syntax.",
            DiagramType.ER: "Generate a Mermaid ER diagram syntax.",
            DiagramType.GANTT: "Create a Mermaid Gantt chart syntax.",
            DiagramType.MINDMAP: "Create a Mermaid mindmap diagram syntax.",
            DiagramType.AI_ARCHITECTURE: """
                Generate a comprehensive AI architecture diagram for a RAG (Retrieval-Augmented Generation) system with multiple agents.
                
                Instead of returning plain Mermaid syntax, return a structured JSON object that describes a complex architecture with:
                
                1. Nodes - representing components like:
                   - Data Sources
                   - Vector Databases
                   - Embedding Models
                   - LLM Services
                   - Agent Components
                   - User Interfaces
                   - Orchestration Services
                
                2. Connections - representing data flows between components
                
                3. Clusters - grouping related components
                
                4. Subgraphs - representing hierarchical structures
                
                5. Styles - including colors, shapes, and highlighting for components
                
                The JSON should have this structure:
                {
                    "type": "ai_architecture",
                    "title": "RAG System Architecture",
                    "nodes": [
                        {"id": "unique_id", "label": "Component Name", "type": "component_type", "description": "What this component does"}
                    ],
                    "connections": [
                        {"from": "node_id1", "to": "node_id2", "label": "connection description", "type": "data_flow_type"}
                    ],
                    "clusters": [
                        {"id": "cluster_id", "label": "Cluster Name", "nodes": ["node_id1", "node_id2"]}
                    ],
                    "styles": {
                        "node_id": {"color": "hex_color", "shape": "shape_type", "border": "border_style"}
                    }
                }
                
                Make the architecture realistic, comprehensive, and detailed for modern RAG systems with agent workflows.
            """,
            DiagramType.SOFTWARE_ARCHITECTURE: """
                Generate a comprehensive software architecture diagram for the requested system.
                
                Instead of returning plain Mermaid syntax, return a structured JSON object that describes a complex architecture with:
                
                1. Nodes - representing components like:
                   - Frontend components (UI, Client Libraries)
                   - Backend services (APIs, Microservices)
                   - Databases and data stores
                   - External services and integrations
                   - Infrastructure components (Load balancers, Message queues, Caches)
                   - Security components
                
                2. Connections - representing communication between components:
                   - API calls
                   - Database queries 
                   - Event flows
                   - Data transformations
                   - Authentication flows
                
                3. Clusters - grouping related components by:
                   - Layer (frontend, backend, data, infrastructure)
                   - Domain/bounded context
                   - Deployment units
                   - Technology stacks
                
                4. Styles - to visually distinguish different types of components
                
                The JSON should have this structure:
                {
                    "type": "software_architecture",
                    "title": "System Architecture",
                    "nodes": [
                        {"id": "unique_id", "label": "Component Name", "type": "component_type", "description": "What this component does", "technology": "Used technology"}
                    ],
                    "connections": [
                        {"from": "node_id1", "to": "node_id2", "label": "connection description", "type": "communication_type", "protocol": "HTTP/gRPC/etc"}
                    ],
                    "clusters": [
                        {"id": "cluster_id", "label": "Cluster Name", "nodes": ["node_id1", "node_id2"]}
                    ],
                    "styles": {
                        "node_id": {"color": "hex_color", "shape": "shape_type", "border": "border_style"}
                    }
                }
                
                VERY IMPORTANT GUIDELINES:
                1. Always use underscore_separated IDs instead of kebab-case or spaces for node IDs and cluster IDs
                2. Keep connection labels short and concise
                3. Use simple component types that can be easily mapped to standard Mermaid shapes
                4. Avoid special characters in IDs and labels
                5. Return only the JSON structure, do not include any explanatory text around it
                
                Make the architecture realistic, comprehensive, and detailed. Include appropriate patterns like microservices, event-driven architecture, layered architecture, etc. as relevant to the request.
            """
        }

    def _detect_diagram_type(self, query: str) -> DiagramType:
        query = query.lower()
        
        # Check for software architecture specific keywords (broader than just AI)
        software_arch_patterns = [
            # General architecture terms
            "software architecture", "system architecture", "application architecture",
            "high-level design", "system design", "component diagram", "deployment diagram",
            "architectural pattern", "solution architecture", "technical architecture",
            
            # Specific architectural patterns
            "microservice", "microservices", "distributed system", "service-oriented",
            "api gateway", "cloud architecture", "serverless", "event-driven",
            "domain-driven", "layered architecture", "hexagonal architecture", 
            "onion architecture", "clean architecture", "cqrs", "event sourcing",
            "mvc", "model-view-controller", "mvvm", "spa architecture", "monolith",
            "broker pattern", "circuit breaker", "saga pattern", "bulkhead pattern", 
            "strangler pattern", "backends for frontends", "bff pattern", "sidecar pattern",
            "ambassador pattern", "n-tier", "pipeline architecture",
            
            # Cloud-specific architectures
            "cloud-native", "multi-cloud", "hybrid cloud", "container orchestration",
            "kubernetes architecture", "docker architecture", "service mesh", "istio",
            
            # Data architecture patterns
            "data pipeline", "etl architecture", "data lake", "data warehouse",
            "data mesh", "lambda architecture", "kappa architecture",
            
            # Integration patterns
            "integration architecture", "message queue", "broker", "enterprise service bus",
            "api management", "webhook architecture", "pub-sub", "publisher-subscriber"
        ]

        ai_arch_patterns = [
            "ai architecture", "rag architecture", "agent workflow", 
            "llm architecture", "ai system", "agent based", 
            "rag system", "rag app", "ai app architecture", 
            "llm system", "language model architecture", "embedding architecture",
            "conversational ai", "chatbot architecture", "cognitive architecture",
            "machine learning pipeline", "ai assistants", "agent system",
            "multi-agent system", "fine-tuning architecture", "neural architecture"
        ]
            
        # Check for specific software architectural patterns
        if any(phrase in query for phrase in software_arch_patterns):
            return DiagramType.SOFTWARE_ARCHITECTURE
        
        # Check for AI architecture specific keywords
        elif any(phrase in query for phrase in ai_arch_patterns):
            return DiagramType.AI_ARCHITECTURE
            
        # Check for other diagram types
        elif any(word in query for word in ["flow", "process", "workflow", "steps", "algorithm"]):
            return DiagramType.FLOWCHART
        elif any(word in query for word in ["sequence", "interaction", "communication", "message", "api call"]):
            return DiagramType.SEQUENCE
        elif any(word in query for word in ["state", "status", "transition", "lifecycle", "phase"]):
            return DiagramType.STATE
        elif any(word in query for word in ["class", "object", "inheritance", "method", "attribute", "oop"]):
            return DiagramType.CLASS
        elif any(word in query for word in ["entity", "database", "er", "table", "relationship", "schema"]):
            return DiagramType.ER
        elif any(word in query for word in ["timeline", "schedule", "gantt", "project", "task"]):
            return DiagramType.GANTT
        elif any(word in query for word in ["mind", "concept", "brainstorm", "idea", "map", "hierarchy"]):
            return DiagramType.MINDMAP
            
        # Default to software architecture for better chance of success with complex diagrams
        return DiagramType.SOFTWARE_ARCHITECTURE

    async def generate_diagram(self, message: str, options: Optional[Dict] = None) -> DiagramResponse:
        try:
            diagram_type = self._detect_diagram_type(message)
            system_prompt = self.diagram_prompts[diagram_type]
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ]
            
            logger.info(f"Generating diagram of type: {diagram_type.value}")
            
            # Use Claude 3 Opus for complex AI architecture diagrams when available
            # For testing, let's use mixtral for all diagram types
            model = "llama-3.3-70b-versatile"  # Update to the new supported model
            
            try:
                logger.info(f"Calling Groq API with model: {model}")
                completion = await self.groq_client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.2 if diagram_type == DiagramType.AI_ARCHITECTURE else 0.7,
                    max_tokens=4000
                )
                
                content = completion.choices[0].message.content.strip()
                logger.info(f"Received response from Groq API, length: {len(content)}")
                
                if diagram_type in [DiagramType.AI_ARCHITECTURE, DiagramType.SOFTWARE_ARCHITECTURE]:
                    try:
                        # Find JSON content if present in the response
                        json_match = re.search(r'```(?:json)?\s*\n(.*?)\n```', content, re.DOTALL)
                        if json_match:
                            json_content = json_match.group(1)
                        else:
                            # Try to find JSON directly
                            json_content = re.search(r'(\{.*\})', content, re.DOTALL)
                            if json_content:
                                json_content = json_content.group(1)
                            else:
                                json_content = content
                        
                        # Parse JSON structure
                        diagram_data = json.loads(json_content)
                        
                        # Convert to Mermaid syntax
                        syntax = self._convert_ai_architecture_to_diagram(diagram_data)
                        
                        # Store raw data in metadata
                        metadata = {
                            "raw_data": diagram_data,
                            "options": options or {},
                            "model": model,
                            "tokens": completion.usage.total_tokens
                        }
                    except Exception as e:
                        logger.error(f"Error processing architecture JSON: {str(e)}")
                        logger.error(traceback.format_exc())
                        
                        # Fallback to flowchart
                        logger.info("Falling back to flowchart generation")
                        fallback_messages = [
                            {"role": "system", "content": self.diagram_prompts[DiagramType.FLOWCHART]},
                            {"role": "user", "content": message}
                        ]
                        
                        fallback_completion = await self.groq_client.chat.completions.create(
                            model="mixtral-8x7b-v0.1",  # Update here as well
                            messages=fallback_messages,
                            temperature=0.7
                        )
                        
                        syntax = fallback_completion.choices[0].message.content.strip()
                        diagram_type = DiagramType.FLOWCHART
                        
                        metadata = {
                            "error": f"Failed to parse architecture JSON: {str(e)}",
                            "raw_content": content[:500],  # Include part of the raw content for debugging
                            "options": options or {},
                            "model": model,
                            "fallback": "flowchart",
                            "tokens": completion.usage.total_tokens
                        }
                else:
                    syntax = content
                    metadata = {
                        "options": options or {},
                        "model": model,
                        "tokens": completion.usage.total_tokens
                    }
                
                # Generate description
                description_prompt = f"Briefly describe this diagram in one sentence and never mention that this is generated by an AI model:\n{syntax}"
                
                try:
                    description = await self._generate_description(description_prompt)
                except Exception as e:
                    logger.error(f"Error generating description: {str(e)}")
                    description = "A diagram showing the requested architecture components and their relationships."
                
                # Create the response object
                response = DiagramResponse(
                    diagram_type=diagram_type.value,
                    syntax=syntax,
                    description=description,
                    metadata=metadata
                )
                
                return response
                
            except Exception as e:
                logger.error(f"Error calling Groq API: {str(e)}")
                logger.error(traceback.format_exc())
                raise e
                
        except Exception as e:
            logger.error(f"Error in generate_diagram: {str(e)}")
            logger.error(traceback.format_exc())
            raise e

    def _convert_ai_architecture_to_diagram(self, diagram_data: Dict[str, Any]) -> str:
        """
        Converts the structured architecture JSON to a visual diagram format.
        Handles both AI architecture and general software architecture diagrams.
        """
        try:
            if diagram_data.get("type") in ["ai_architecture", "software_architecture"]:
                try:
                    # Start with a flowchart
                    mermaid = "flowchart TD\n"
                    
                    # Add diagram title
                    mermaid += f"    title[\"{diagram_data.get('title', 'Architecture Diagram')}\"]\n"
                    
                    # Process clusters/subgraphs - by layer or domain
                    for cluster in diagram_data.get("clusters", []):
                        cluster_id = cluster.get("id", "").replace("-", "_")
                        cluster_label = cluster.get("label", "")
                        # Proper Mermaid subgraph syntax with quoted label
                        mermaid += f"    subgraph {cluster_id}[\"{cluster_label}\"]\n"
                        for node_id in cluster.get("nodes", []):
                            node_id = node_id.replace("-", "_")
                            mermaid += f"        {node_id}\n"
                        mermaid += "    end\n"
                    
                    # Process nodes with appropriate shapes based on their type
                    for node in diagram_data.get("nodes", []):
                        node_id = node.get("id", "").replace("-", "_")
                        label = node.get("label", "")
                        node_type = node.get("type", "").lower()
                        technology = node.get("technology", "")
                        
                        # If technology is specified, add it to the label
                        if technology and not label.endswith(f"({technology})"):
                            label = f"{label} ({technology})"
                        
                        # Apply styling based on node type for both AI and software architecture
                        # Using standard Mermaid shapes for compatibility
                        if node_type in ["ui", "user_interface", "frontend", "client", "web", "mobile"]:
                            # Standard rectangular shape for UI components
                            mermaid += f"    {node_id}[\"{label}\"]\n"
                        elif node_type in ["database", "db", "data_store", "storage", "persistence"]:
                            # Database cylinder shape 
                            mermaid += f"    {node_id}[(\"{label}\")]\n"
                        elif node_type in ["vector_db", "vector_database", "document_store"]:
                            # Database cylinder shape
                            mermaid += f"    {node_id}[(\"{label}\")]\n"
                        elif node_type in ["api", "service", "microservice", "endpoint", "gateway"]:
                            # Standard rectangular shape for services
                            mermaid += f"    {node_id}[\"{label}\"]\n"
                        elif node_type in ["llm", "model", "ml_model", "ai_component"]:
                            # Standard rectangular shape for ML models
                            mermaid += f"    {node_id}[\"{label}\"]\n"
                        elif node_type in ["agent", "worker", "processor", "consumer", "daemon"]:
                            # Hexagon shape for agent/worker components
                            mermaid += f"    {node_id}{{\"{label}\"}}\n"
                        elif node_type in ["processing", "function", "compute", "lambda", "serverless"]:
                            # Subroutine shape for processing components
                            mermaid += f"    {node_id}[[\"{label}\"]]\n"
                        elif node_type in ["queue", "message_broker", "event_bus", "kafka", "rabbitmq"]:
                            # Standard rectangular shape for queues
                            mermaid += f"    {node_id}[\"{label}\"]\n"
                        elif node_type in ["cache", "redis", "memcached"]:
                            # Standard rectangular shape for caches
                            mermaid += f"    {node_id}[\"{label}\"]\n"
                        elif node_type in ["load_balancer", "proxy", "routing"]:
                            # Standard rectangular shape for load balancers
                            mermaid += f"    {node_id}[\"{label}\"]\n"
                        elif node_type in ["external", "third_party", "external_service"]:
                            # Standard rectangular shape for external services
                            mermaid += f"    {node_id}[\"{label}\"]\n"
                        elif node_type in ["auth", "authentication", "security", "identity"]:
                            # Standard rectangular shape for auth services
                            mermaid += f"    {node_id}[\"{label}\"]\n"
                        else:
                            # Default to rectangle for unknown types
                            mermaid += f"    {node_id}[\"{label}\"]\n"
                    
                    # Process connections with appropriate styling
                    for connection in diagram_data.get("connections", []):
                        from_id = connection.get("from", "").replace("-", "_")
                        to_id = connection.get("to", "").replace("-", "_")
                        label = connection.get("label", "")
                        conn_type = connection.get("type", "").lower()
                        protocol = connection.get("protocol", "")
                        
                        # Add protocol to label if specified
                        if protocol and not label.endswith(f"({protocol})"):
                            if label:
                                label = f"{label} ({protocol})"
                            else:
                                label = protocol
                        
                        # Create the simplest connection with no label - guaranteed to work
                        if conn_type in ["response", "return", "callback", "data_flow", "etl", "stream", "batch"]:
                            # Dotted arrow
                            mermaid += f"    {from_id} -.-> {to_id}\n"
                        else:
                            # Standard arrow for all other connection types
                            mermaid += f"    {from_id} --> {to_id}\n"
                    
                    # Process styles
                    if "styles" in diagram_data:
                        for node_id, style in diagram_data.get("styles", {}).items():
                            node_id = node_id.replace("-", "_")
                            color = style.get("color", "#FFFFFF")
                            border = style.get("border", "#000000")
                            mermaid += f"    style {node_id} fill:{color},stroke:{border}\n"
                    
                    # Apply standard styling to certain node types for consistency
                    # Loop through all nodes again to apply default styling by type
                    for node in diagram_data.get("nodes", []):
                        node_id = node.get("id", "").replace("-", "_")
                        node_type = node.get("type", "").lower()
                        
                        # Only apply default styling if not already styled
                        if "styles" not in diagram_data or node_id not in diagram_data.get("styles", {}):
                            # Apply standard styling based on component type
                            if node_type in ["ui", "frontend", "client", "web", "mobile"]:
                                mermaid += f"    style {node_id} fill:#D4F1F9,stroke:#1E90FF\n"
                            elif node_type in ["database", "db", "data_store", "persistence"]:
                                mermaid += f"    style {node_id} fill:#E1D5E7,stroke:#9673A6\n"
                            elif node_type in ["vector_db", "vector_database"]:
                                mermaid += f"    style {node_id} fill:#DAE8FC,stroke:#6C8EBF\n"
                            elif node_type in ["api", "service", "microservice"]:
                                mermaid += f"    style {node_id} fill:#F5F5F5,stroke:#666666\n"
                            elif node_type in ["llm", "model", "ml_model"]:
                                mermaid += f"    style {node_id} fill:#FFE6CC,stroke:#D79B00\n"
                            elif node_type in ["queue", "message_broker", "event_bus"]:
                                mermaid += f"    style {node_id} fill:#FFF2CC,stroke:#D6B656\n"
                            elif node_type in ["auth", "security"]:
                                mermaid += f"    style {node_id} fill:#F8CECC,stroke:#B85450\n"
                            elif node_type in ["cache"]:
                                mermaid += f"    style {node_id} fill:#D5E8D4,stroke:#82B366\n"
                            elif node_type in ["external", "third_party"]:
                                mermaid += f"    style {node_id} fill:#F5F5F5,stroke:#666666\n"
                    
                    # Style the title node
                    mermaid += f"    style title fill:#FFFFFF,stroke:#FFFFFF,color:#000000,font-size:16px\n"
                    
                    return mermaid
                except Exception as e:
                    logger.error(f"Error converting architecture to Mermaid: {str(e)}")
                    logger.error(traceback.format_exc())
                    
                    # Return a simplified fallback diagram instead of error text
                    fallback = "flowchart TD\n"
                    fallback += f"    title[\"Architecture Diagram - Error in Conversion\"]\n"
                    fallback += f"    A[\"Error converting diagram: {str(e)[:50]}...\"]\n"
                    fallback += f"    style title fill:#FFFFFF,stroke:#FFFFFF,color:#000000,font-size:16px\n"
                    fallback += f"    style A fill:#F8CECC,stroke:#B85450\n"
                    return fallback
            
            # If it's not an architecture diagram or conversion fails, return a basic flowchart
            # with error message - don't return raw JSON which will fail parsing
            return "flowchart TD\n    A[\"Diagram data received but conversion not supported\"]\n    style A fill:#F5F5F5,stroke:#666666\n"
        except Exception as e:
            logger.error(f"Unexpected error in _convert_ai_architecture_to_diagram: {str(e)}")
            logger.error(traceback.format_exc())
            return f"flowchart TD\n    A[\"Error: {str(e)[:100]}\"]"

    async def _generate_description(self, prompt: str) -> str:
        try:
            completion = await self.groq_client.chat.completions.create(
                model="mixtral-8x7b-v0.1",  # Update here as well
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7
            )
            return completion.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error generating description: {str(e)}")
            return "A diagram showing the requested architecture components and their relationships."

    async def process_message(
        self,
        user_id: str,
        message: str,
        session_id: Optional[UUID] = None,
        generate_diagram: bool = False
    ) -> Union[ChatSession, DiagramResponse]:
        if generate_diagram:
            return await self.generate_diagram(message)
            
        if session_id and session_id in self.sessions:
            session = self.sessions[session_id]
        else:
            session = ChatSession(user_id=user_id)
            self.sessions[session.id] = session
        
        user_message = Message(content=message, role="user")
        session.messages.append(user_message)
        
        try:
            completion = await self.groq_client.chat.completions.create(
                model="mixtral-8x7b-v0.1",  # Update here as well
                messages=[{"role": m.role, "content": m.content} for m in session.messages],
                temperature=0.7
            )
            
            response = completion.choices[0].message.content
            
            assistant_message = Message(content=response, role="assistant")
            session.messages.append(assistant_message)
            
            return session
        except Exception as e:
            raise Exception(f"Error processing message: {str(e)}")

# Create singleton instance
diagram = DiagramChatbot()
