# BankShield: Архитектурные диаграммы

Этот документ содержит детальные диаграммы архитектуры системы BankShield в формате Mermaid.

## 1. Общая архитектура системы (High-Level)

```mermaid
graph TB
    subgraph "Data Generation"
        PG[Python Generator<br/>Генерация транзакций<br/>Interval: 60s]
    end
    
    subgraph "Operational Database"
        MONGO[(MongoDB<br/>banking_data<br/>transactions)]
    end
    
    subgraph "Orchestration"
        AIRFLOW[Apache Airflow 2.8.0]
        DAG1[transactions_el DAG<br/>Schedule: */30 * * * *]
        DAG2[dbt_transformations DAG<br/>Schedule: 0 * * * *]
    end
    
    subgraph "Analytics Database"
        PG_DB[(PostgreSQL<br/>analytics_db)]
        STG[STG Schema<br/>Views]
        ODS[ODS Schema<br/>Tables]
        DWH[DWH Schema<br/>Incremental Tables]
        DM[DM Schema<br/>Business Marts]
    end
    
    subgraph "Visualization"
        GRAFANA[Grafana<br/>Dashboards]
        ELEM[Elementary UI<br/>Data Quality]
    end
    
    subgraph "API Layer"
        API[REST API<br/>FastAPI<br/>Port: 8100]
    end
    
    PG -->|Insert| MONGO
    MONGO -->|Extract| DAG1
    DAG1 -->|Load RAW| PG_DB
    PG_DB --> DAG2
    DAG2 -->|Transform| STG
    STG --> ODS
    ODS --> DWH
    DWH --> DM
    DM -->|Query| GRAFANA
    DM -->|Monitor| ELEM
    MONGO <-->|CRUD| API
    
    style PG fill:#e1f5ff
    style MONGO fill:#4caf50
    style AIRFLOW fill:#ff9800
    style PG_DB fill:#2196f3
    style GRAFANA fill:#f44336
    style API fill:#9c27b0
```

## 2. Поток данных (Data Flow)

```mermaid
sequenceDiagram
    participant Gen as Python Generator
    participant Mongo as MongoDB
    participant Air as Airflow
    participant PG as PostgreSQL
    participant DBT as DBT
    participant Graf as Grafana
    participant User as End User
    
    Note over Gen: Every 60 seconds
    Gen->>Mongo: Insert transaction
    
    Note over Air: Every 30 minutes
    Air->>Mongo: Extract new transactions
    Air->>PG: Load to RAW table
    
    Note over Air: Every hour
    Air->>DBT: Trigger transformations
    DBT->>PG: STG (Views)
    DBT->>PG: ODS (Tables)
    DBT->>PG: DWH (Incremental)
    DBT->>PG: DM (Business Marts)
    
    Note over Graf: Real-time
    Graf->>PG: Query DM tables
    Graf-->>User: Display dashboard
    
    User->>Graf: View metrics
```

## 3. DBT Трансформации (Layered Architecture)

```mermaid
graph LR
    subgraph "Source"
        RAW[(PostgreSQL<br/>public.transactions)]
    end
    
    subgraph "STG Layer"
        STG1[stg_transactions<br/>Materialization: VIEW<br/>- Parse JSON<br/>- Clean data<br/>- Validate fields<br/>- Normalize types]
    end
    
    subgraph "ODS Layer"
        ODS1[ods_transactions<br/>Materialization: TABLE<br/>- Business rules<br/>- Risk categories<br/>- Amount categories<br/>- Filter invalid]
    end
    
    subgraph "DWH Layer"
        DWH1[dwh_transactions_daily<br/>Materialization: INCREMENTAL<br/>- Daily aggregates<br/>- Merge by date]
        DWH2[dwh_user_transactions<br/>Materialization: INCREMENTAL<br/>- User aggregates<br/>- Merge by user_id]
    end
    
    subgraph "DM Layer"
        DM1[dm_fraud_analysis<br/>Materialization: TABLE<br/>- Fraud metrics<br/>- High-risk users]
        DM2[dm_transaction_summary<br/>Materialization: TABLE<br/>- Overall stats<br/>- Currency breakdown<br/>- Country breakdown]
    end
    
    RAW --> STG1
    STG1 --> ODS1
    ODS1 --> DWH1
    ODS1 --> DWH2
    DWH1 --> DM1
    DWH1 --> DM2
    DWH2 --> DM1
    
    style RAW fill:#e0e0e0
    style STG1 fill:#bbdefb
    style ODS1 fill:#90caf9
    style DWH1 fill:#64b5f6
    style DWH2 fill:#64b5f6
    style DM1 fill:#42a5f5
    style DM2 fill:#42a5f5
```

## 4. Airflow DAGs

```mermaid
graph TB
    subgraph "transactions_el DAG"
        START1[Start]
        EXTRACT[Extract from MongoDB<br/>Filter: timestamp > last_run]
        VALIDATE[Validate data]
        LOAD[Load to PostgreSQL<br/>Table: transactions]
        END1[End]
        
        START1 --> EXTRACT
        EXTRACT --> VALIDATE
        VALIDATE --> LOAD
        LOAD --> END1
    end
    
    subgraph "dbt_transformations DAG"
        START2[Start]
        DEPS[dbt deps<br/>Install packages]
        
        subgraph "STG Models"
            STG_RUN[dbt run --select stg.*]
            STG_TEST[dbt test --select stg.*]
        end
        
        subgraph "ODS Models"
            ODS_RUN[dbt run --select ods.*]
            ODS_TEST[dbt test --select ods.*]
        end
        
        subgraph "DWH Models"
            DWH_RUN[dbt run --select dwh.*]
            DWH_TEST[dbt test --select dwh.*]
        end
        
        subgraph "DM Models"
            DM_RUN[dbt run --select dm.*]
            DM_TEST[dbt test --select dm.*]
        end
        
        CUSTOM_TEST[Custom Tests]
        ELEM_RUN[Elementary Anomaly Detection]
        DOCS[Generate Documentation]
        END2[End]
        
        START2 --> DEPS
        DEPS --> STG_RUN
        STG_RUN --> STG_TEST
        STG_TEST --> ODS_RUN
        ODS_RUN --> ODS_TEST
        ODS_TEST --> DWH_RUN
        DWH_RUN --> DWH_TEST
        DWH_TEST --> DM_RUN
        DM_RUN --> DM_TEST
        DM_TEST --> CUSTOM_TEST
        CUSTOM_TEST --> ELEM_RUN
        ELEM_RUN --> DOCS
        DOCS --> END2
    end
    
    style START1 fill:#4caf50
    style END1 fill:#f44336
    style START2 fill:#4caf50
    style END2 fill:#f44336
```

## 5. Компоненты и их взаимодействие

```mermaid
graph TB
    subgraph "Application Layer"
        COLLECTOR[Data Collector<br/>Python 3.11<br/>- Generate transactions<br/>- Insert to MongoDB]
        API[REST API<br/>FastAPI<br/>- /health<br/>- /transactions<br/>- /stats]
    end
    
    subgraph "Storage Layer"
        MONGO[(MongoDB<br/>Port: 27017<br/>DB: banking_data<br/>Collection: transactions)]
        POSTGRES[(PostgreSQL<br/>Port: 5433<br/>DB: analytics_db<br/>Schemas: public, stg, ods, dwh, dm)]
        AIRFLOW_PG[(Airflow PostgreSQL<br/>Port: 5432<br/>DB: airflow)]
    end
    
    subgraph "Orchestration Layer"
        WEBSERVER[Airflow Webserver<br/>Port: 8080<br/>UI for monitoring]
        SCHEDULER[Airflow Scheduler<br/>Execute DAGs]
        INIT[Airflow Init<br/>DB migration<br/>Create admin user]
    end
    
    subgraph "Transformation Layer"
        DBT[DBT<br/>- Models<br/>- Tests<br/>- Documentation]
        ELEM[Elementary<br/>- Anomaly detection<br/>- Data quality]
    end
    
    subgraph "Visualization Layer"
        GRAFANA[Grafana<br/>Port: 3001<br/>Dashboards]
        ELEM_UI[Elementary UI<br/>Port: 8081<br/>Reports]
    end
    
    COLLECTOR -->|Insert| MONGO
    API <-->|CRUD| MONGO
    
    SCHEDULER -->|Extract| MONGO
    SCHEDULER -->|Load| POSTGRES
    SCHEDULER -->|Execute| DBT
    
    DBT -->|Transform| POSTGRES
    DBT -->|Run| ELEM
    
    GRAFANA -->|Query| POSTGRES
    ELEM_UI -->|Read| POSTGRES
    
    WEBSERVER -->|Metadata| AIRFLOW_PG
    SCHEDULER -->|Metadata| AIRFLOW_PG
    INIT -->|Setup| AIRFLOW_PG
    
    style COLLECTOR fill:#e1f5ff
    style API fill:#9c27b0
    style MONGO fill:#4caf50
    style POSTGRES fill:#2196f3
    style GRAFANA fill:#f44336
```

## 6. Масштабирование архитектуры

```mermaid
graph TB
    subgraph "Load Balancer"
        LB[Nginx / HAProxy]
    end
    
    subgraph "API Tier (Horizontal Scaling)"
        API1[API Instance 1]
        API2[API Instance 2]
        API3[API Instance 3]
        API4[API Instance 4]
        API5[API Instance 5]
    end
    
    subgraph "Data Tier (Replica Set)"
        MONGO_PRIMARY[(MongoDB Primary<br/>Read/Write)]
        MONGO_SECONDARY1[(MongoDB Secondary 1<br/>Read Only)]
        MONGO_SECONDARY2[(MongoDB Secondary 2<br/>Read Only)]
    end
    
    subgraph "Analytics Tier (Primary + Replicas)"
        PG_PRIMARY[(PostgreSQL Primary<br/>Write)]
        PG_REPLICA1[(PostgreSQL Replica 1<br/>Read)]
        PG_REPLICA2[(PostgreSQL Replica 2<br/>Read)]
    end
    
    subgraph "Orchestration Tier (Celery)"
        AIRFLOW_WEB[Airflow Webserver]
        AIRFLOW_SCHED[Airflow Scheduler]
        CELERY1[Celery Worker 1]
        CELERY2[Celery Worker 2]
        CELERY3[Celery Worker 3]
        REDIS[(Redis<br/>Message Broker)]
    end
    
    subgraph "Visualization Tier"
        GRAFANA1[Grafana Instance 1]
        GRAFANA2[Grafana Instance 2]
    end
    
    LB --> API1
    LB --> API2
    LB --> API3
    LB --> API4
    LB --> API5
    
    API1 --> MONGO_PRIMARY
    API2 --> MONGO_SECONDARY1
    API3 --> MONGO_SECONDARY2
    API4 --> MONGO_PRIMARY
    API5 --> MONGO_SECONDARY1
    
    MONGO_PRIMARY -.Replication.-> MONGO_SECONDARY1
    MONGO_PRIMARY -.Replication.-> MONGO_SECONDARY2
    
    AIRFLOW_SCHED --> REDIS
    REDIS --> CELERY1
    REDIS --> CELERY2
    REDIS --> CELERY3
    
    CELERY1 --> PG_PRIMARY
    CELERY2 --> PG_PRIMARY
    CELERY3 --> PG_PRIMARY
    
    PG_PRIMARY -.Replication.-> PG_REPLICA1
    PG_PRIMARY -.Replication.-> PG_REPLICA2
    
    GRAFANA1 --> PG_REPLICA1
    GRAFANA2 --> PG_REPLICA2
    
    style LB fill:#ff9800
    style MONGO_PRIMARY fill:#4caf50
    style PG_PRIMARY fill:#2196f3
    style REDIS fill:#f44336
```

## 7. Deployment Architecture

```mermaid
graph TB
    subgraph "Production Server (Yandex Cloud)"
        subgraph "Docker Compose Network"
            subgraph "Application Containers"
                DC[data-collector]
                API_C[bankshield-api]
            end
            
            subgraph "Database Containers"
                MONGO_C[mongodb_prod]
                PG_C[postgres_analytics]
                APG_C[airflow-postgres]
            end
            
            subgraph "Airflow Containers"
                INIT_C[airflow-init]
                WEB_C[airflow-webserver]
                SCHED_C[airflow-scheduler]
            end
            
            subgraph "Monitoring Containers"
                GRAF_C[grafana]
                ELEM_C[elementary-ui]
            end
        end
        
        subgraph "Volumes"
            V1[postgres_data]
            V2[mongodb_data]
            V3[airflow_postgres_data]
            V4[grafana_data]
            V5[elementary_reports]
        end
        
        subgraph "Exposed Ports"
            P1[5433:5432 - PostgreSQL]
            P2[27017:27017 - MongoDB]
            P3[8080:8080 - Airflow]
            P4[8100:8000 - API]
            P5[3001:3000 - Grafana]
            P6[8081:8081 - Elementary]
        end
    end
    
    subgraph "External Access"
        USERS[Users / External Systems]
    end
    
    DC --> MONGO_C
    API_C --> MONGO_C
    WEB_C --> APG_C
    SCHED_C --> APG_C
    SCHED_C --> MONGO_C
    SCHED_C --> PG_C
    GRAF_C --> PG_C
    ELEM_C --> PG_C
    
    MONGO_C -.Mount.-> V2
    PG_C -.Mount.-> V1
    APG_C -.Mount.-> V3
    GRAF_C -.Mount.-> V4
    ELEM_C -.Mount.-> V5
    
    USERS -->|HTTP| P3
    USERS -->|HTTP| P4
    USERS -->|HTTP| P5
    USERS -->|HTTP| P6
    
    style DC fill:#e1f5ff
    style API_C fill:#9c27b0
    style MONGO_C fill:#4caf50
    style PG_C fill:#2196f3
    style GRAF_C fill:#f44336
```

## 8. API Request Flow

```mermaid
sequenceDiagram
    participant Client
    participant API as FastAPI
    participant Mongo as MongoDB
    participant Valid as Validator
    participant Logger
    
    Client->>API: POST /transactions
    API->>Valid: Validate request
    
    alt Valid request
        Valid-->>API: OK
        API->>Mongo: Check connection
        
        alt MongoDB connected
            Mongo-->>API: Connected
            API->>API: Generate transaction
            API->>Mongo: Insert document
            Mongo-->>API: Success
            API->>Logger: Log success
            API-->>Client: 200 OK {transaction_id}
        else MongoDB disconnected
            Mongo-->>API: Connection error
            API->>Mongo: Attempt reconnect
            alt Reconnect success
                API->>Mongo: Insert document
                Mongo-->>API: Success
                API-->>Client: 200 OK {transaction_id}
            else Reconnect failed
                API->>Logger: Log error
                API-->>Client: 503 Service Unavailable
            end
        end
    else Invalid request
        Valid-->>API: Validation error
        API->>Logger: Log validation error
        API-->>Client: 422 Unprocessable Entity
    end
```

## 9. Data Quality Monitoring Flow

```mermaid
graph TB
    subgraph "DBT Run"
        RUN[dbt run]
        TEST[dbt test]
    end
    
    subgraph "Elementary Monitoring"
        COLLECT[Collect test results]
        ANOMALY[Anomaly detection]
        SCHEMA[Schema change detection]
    end
    
    subgraph "Alerts & Reports"
        REPORT[Generate HTML report]
        ALERT[Send alerts]
        UI[Elementary UI]
    end
    
    subgraph "Data Quality Checks"
        CHECK1[Uniqueness tests]
        CHECK2[Not null tests]
        CHECK3[Accepted values tests]
        CHECK4[Custom tests]
        CHECK5[Freshness tests]
    end
    
    RUN --> TEST
    TEST --> CHECK1
    TEST --> CHECK2
    TEST --> CHECK3
    TEST --> CHECK4
    TEST --> CHECK5
    
    CHECK1 --> COLLECT
    CHECK2 --> COLLECT
    CHECK3 --> COLLECT
    CHECK4 --> COLLECT
    CHECK5 --> COLLECT
    
    COLLECT --> ANOMALY
    COLLECT --> SCHEMA
    
    ANOMALY --> REPORT
    SCHEMA --> REPORT
    
    REPORT --> UI
    REPORT --> ALERT
    
    style RUN fill:#4caf50
    style TEST fill:#ff9800
    style ANOMALY fill:#f44336
    style REPORT fill:#2196f3
```

## 10. Future Architecture (с ML и Real-time)

```mermaid
graph TB
    subgraph "Data Sources"
        APP[Banking App]
        ATM[ATM Transactions]
        WEB[Web Transactions]
    end
    
    subgraph "Real-time Layer"
        KAFKA[Apache Kafka]
        STREAM[Stream Processor<br/>Kafka Streams / Flink]
    end
    
    subgraph "Feature Store"
        REDIS_FS[(Redis<br/>Online Features)]
        S3[(S3 / MinIO<br/>Offline Features)]
    end
    
    subgraph "ML Layer"
        TRAIN[Model Training<br/>XGBoost / Neural Net]
        SERVE[Model Serving<br/>TensorFlow Serving]
        REGISTRY[Model Registry<br/>MLflow]
    end
    
    subgraph "Storage"
        MONGO[(MongoDB)]
        POSTGRES[(PostgreSQL)]
        TIMESCALE[(TimescaleDB)]
    end
    
    subgraph "Analytics"
        DBT[DBT]
        GRAFANA[Grafana]
    end
    
    APP --> KAFKA
    ATM --> KAFKA
    WEB --> KAFKA
    
    KAFKA --> STREAM
    STREAM --> REDIS_FS
    STREAM --> MONGO
    
    REDIS_FS --> SERVE
    SERVE --> STREAM
    
    MONGO --> DBT
    DBT --> POSTGRES
    
    POSTGRES --> S3
    S3 --> TRAIN
    TRAIN --> REGISTRY
    REGISTRY --> SERVE
    
    POSTGRES --> GRAFANA
    TIMESCALE --> GRAFANA
    
    style KAFKA fill:#ff9800
    style STREAM fill:#f44336
    style REDIS_FS fill:#e91e63
    style SERVE fill:#9c27b0
    style TRAIN fill:#673ab7
```

---

## Легенда

### Цвета компонентов
- 🔵 **Синий** - Базы данных (PostgreSQL)
- 🟢 **Зеленый** - NoSQL БД (MongoDB)
- 🟠 **Оранжевый** - Оркестрация (Airflow)
- 🔴 **Красный** - Визуализация (Grafana)
- 🟣 **Фиолетовый** - API (FastAPI)
- ⚪ **Серый** - Утилиты и вспомогательные компоненты

### Типы связей
- **Сплошная линия** → Основной поток данных
- **Пунктирная линия** ⇢ Репликация / Синхронизация
- **Двунаправленная** ↔ CRUD операции

