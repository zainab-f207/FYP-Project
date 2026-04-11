# SAFEVISION: Project Documentation Diagrams (v2.2)

This file contains 9 high-clarity, white-themed diagrams optimized for printing and documentation. These diagrams reflect the actual implementation of the SafeVision project while removing obsolete features (Community/Groups/Patrol) and marking the Mobile App as a future phase.

---

## 4.8: System Architecture
Vertical high-contrast layout for maximum readability.

```mermaid
graph TD
    classDef default fill:#ffffff,stroke:#000000,stroke-width:2px,color:#000000;
    classDef future fill:#f5f5f5,stroke:#999999,stroke-width:2px,stroke-dasharray: 5 5,color:#666666;

    subgraph Client_Layer [CLIENT LAYER]
        A["Web Dashboard (React.js)"]
        B["Capacitor App (Future Phase)"]:::future
    end

    subgraph App_Server [APPLICATION SERVER]
        direction TB
        C1["FastAPI Backend (Uvicorn)"]
        C2["APScheduler (Background Jobs)"]
        
        subgraph Logic_Units [CORE SERVICES]
            L1["Poisson / RF Prediction Engine"]
            L2["Multi-Channel Alert Dispatcher"]
            L3["FIRExtractor OCR Service"]
            L4["Emergency SOS Dispatch System"]
        end
    end

    subgraph Persistence [DATA LAYER]
        D[("MySQL Primary Database")]
    end

    subgraph External_API [EXTERNAL GATEWAYS]
        E1["OpenStreetMap Tiles (GIS)"]
        E2["SMTP Server (Email Alerts)"]
    end

    A <-->|REST / WebSockets| C1
    B -.->|Planned Link| C1
    C1 <-->|SQL Queries| D
    C2 -->|Trigger Polling| L2
    C1 --> E1
    C1 --> E2
```

---

## 4.9: Logical View (Class Diagram)
Reflects the core entities used in the Safety Analytics Dashboard.

```mermaid
classDiagram
    direction TB
    class UserAccount {
        +int id
        +string email
        +string role
        +triggerSOS()
        +updateProfile()
    }
    class AdminAccount {
        +string department
        +json permissions
        +approveCrimes()
        +viewReports()
    }
    class IncidentData {
        +int id
        +string crime_type
        +decimal risk_score
        +datetime date_time
        +getMetricSummary()
    }
    class DashboardAlert {
        +string title
        +string severity
        +bool is_read
        +markProcessed()
    }
    UserAccount <|-- AdminAccount : Specialized Role
    UserAccount "1" --> "*" DashboardAlert : Receives
    IncidentData "*" -- "1" GeographicArea : Mapped to
```

---

## 4.10: Process View (Activity Diagram)
Workflow for risk prediction with model fallbacks.

```mermaid
graph TD
    START((START)) --> INPUT[Receive Analysis Request]
    INPUT --> FETCH[Query Historical Crime Data]
    FETCH --> P_MODE{Poisson Model?}
    
    P_MODE -- Success --> AGG[Aggregate Result]
    P_MODE -- Fail --> RF_MODE{Random Forest?}
    
    RF_MODE -- Success --> AGG
    RF_MODE -- Fail --> LEGACY[Legacy Fallback Model]
    
    LEGACY --> AGG
    AGG --> CHECK{Risk Threshold?}
    
    CHECK -- "> 50% Significant Risk" --> GEN[Generate Safety Alert]
    CHECK -- "Safe / Low Risk" --> LOG[Log Query Activity]
    
    GEN --> LOG
    LOG --> END((END))
```

---

## 4.11: System State Diagram
Transitions between major application states.

```mermaid
stateDiagram-v2
    direction TB
    [*] --> Standby
    Standby --> Verifying : User Login
    Verifying --> Standby : Fail
    Verifying --> Dashboard_View : Success
    
    state Dashboard_View {
        [*] --> Map_Loading
        Map_Loading --> Active_Monitoring
        Active_Monitoring --> Predicting : Location Change
        Predicting --> Data_Ready
        Data_Ready --> Dispatch_Alert : Risk High
        Dispatch_Alert --> Active_Monitoring
        Data_Ready --> Active_Monitoring
    }
    
    Dashboard_View --> SOS_Triggered : SOS Interaction
    SOS_Triggered --> Dashboard_View : Issue Resolved
```

---

## 4.12: Sequence Diagram (Real-time Polling)
Messaging between background workers and the user interface.

```mermaid
sequenceDiagram
    autonumber
    participant Job as APScheduler
    participant Backend as FastAPI App
    participant DB as MySQL Database
    participant UI as React Frontend

    Job->>Backend: Process Incident Buffer (2m)
    Backend->>DB: Fetch New Approved Incidents
    DB-->>Backend: Results List
    Backend->>DB: Scan User Radius Coordinates
    DB-->>Backend: Matches Found
    Backend->>UI: Emit WebSocket / Push Alert
    Backend->>DB: Update Notification History
    UI-->>Backend: UI Refresh Ack
```

---

## 4.13: Development View (Components)
Modular structure for build management.

```mermaid
graph LR
    subgraph UI_Modules [FRONTEND COMPONENTS]
        direction TB
        F1[Map Intelligence]
        F2[Safety Radar/Charts]
        F3[OCR FIR Scanner]
        F4[SOS Console]
    end

    subgraph Service_Modules [BACKEND SERVICES]
        direction TB
        B1[Risk Engine]
        B2[Auth / Token Mgr]
        B3[Alert System]
        B4[Reporter API]
    end

    subgraph Storage_Layer [DATA OPS]
        D[(MySQL Storage)]
    end

    UI_Modules --> Service_Modules
    Service_Modules --> Storage_Layer
```

---

## 4.14: Physical (Deployment) Diagram
Infrastructure mapping for production.

```mermaid
graph TD
    classDef node fill:#ffffff,stroke:#333,stroke-width:2px;

    subgraph End_User [USER ENVIRONMENT]
        Dev["User Terminal (Browser)"]:::node
    end

    subgraph Web_Tier [APPLICATION CLOUD]
        direction TB
        LB["Nginx Proxy / SSL"]:::node
        APP["FastAPI Application"]:::node
        SCH["Job Scheduler"]:::node
    end

    subgraph Data_Tier [DATABASE CLOUD]
        MDB["Primary MySQL 8.0 Instance"]:::node
    end

    Dev <-->|HTTPS port 443| LB
    LB <-->|Local TCP port 8000| APP
    APP <-->|SQL TCP port 3306| MDB
```

---

## 4.15: Entity Relationship Diagram (ERD)
Simplified schema focused on core features.

```mermaid
erDiagram
    users_info ||--o{ user_alerts : "receives"
    users_info ||--o{ user_location_history : "logs path"
    users_info ||--o{ emergency_calls : "triggers SOS"
    
    crimes }|--|| areas : "assigned to"
    
    admins ||--o{ audit_logs : "tracks actions"
    admins ||--o{ approval_requests : "validates FIRs"

    users_info {
        int id PK
        string email
        string role
        bool is_verified
    }
    crimes {
        int id PK
        string crime_type
        decimal latitude
        decimal longitude
        string severity
    }
    user_alerts {
        int id PK
        int user_id FK
        string title
        bool is_read
    }
```

---

## 4.16: Context Diagram (DFD Level 0)
Highest level flow of data into and out of SafeVision.

```mermaid
graph LR
    U((MOBILE/WEB USER)) -- "Credentials / GPS" --> S(SAFEVISION SYSTEM)
    A((SYSTEM ADMIN)) -- "Upload / Approve FIRs" --> S
    S -- "Analytics / Risk Alerts" --> U
    S -- "System Logs / Reports" --> A
    
    GIS((OSM Mapping API)) -- "Map Layers" --> S
    MAIL((SMTP Gateway)) -- "Email Alerts" --> S
```

---

> [!TIP]
> Ensure your markdown viewer supports **Mermaid** rendering to view these diagrams. From the viewer, you can export these as high-resolution images for your final Word/PDF documentation.
