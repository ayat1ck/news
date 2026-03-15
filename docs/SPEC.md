# TECHNICAL SPECIFICATION

# Automated News Aggregation & Publishing System

## 1. Project Overview

The system is an automated platform designed to collect, process,
analyze, and publish news from multiple sources including Telegram
channels and RSS feeds.

The system must:

-   Collect news automatically
-   Remove duplicates (including semantic duplicates)
-   Rewrite and structure news using AI
-   Provide moderation tools
-   Publish content to a public website
-   Publish content to Telegram channels
-   Provide a full administrative interface
-   Support extensibility and scalability

This system should be production-ready and designed with long-term
scalability and maintainability in mind.

------------------------------------------------------------------------

# 2. System Architecture

The system will follow a modular monolithic architecture with background
workers.

### Core Components

1.  Backend API
2.  Public Website
3.  Admin Panel
4.  Background Workers
5.  Database
6.  Queue System
7.  AI Processing Layer

------------------------------------------------------------------------

## High-Level Architecture

Sources (Telegram / RSS) → Collectors → Raw Storage (PostgreSQL) →
Processing Pipeline - Normalization - Filtering - Deduplication -
Semantic Analysis - AI Rewrite → Moderation Queue → Publishing System -
Website - Telegram

------------------------------------------------------------------------

# 3. Technology Stack

## Backend

FastAPI (Python)

## Frontend

Next.js (Public website + Admin panel)

## Database

PostgreSQL

## Queue System

Redis + Celery

## Containerization

Docker + Docker Compose

Services: - backend - frontend - postgres - redis - workers

------------------------------------------------------------------------

# 4. Core Functional Modules

## 4.1 Source Management

Sources must be configurable through the admin panel.

Supported source types:

### Telegram

Fields: - id - channel_username - language - topic - priority -
is_active - last_collected_at

### RSS Feeds

Fields: - id - feed_url - site_name - language - topic - priority -
is_active - last_collected_at

Optional: website parsing fallback.

------------------------------------------------------------------------

## 4.2 News Collection

Collectors run periodically using Celery.

Tasks:

-   collect_telegram_posts
-   collect_rss_entries
-   fetch_article_content

Default frequency: Every 1 hour.

------------------------------------------------------------------------

## 4.3 Raw News Storage

Table: raw_items

Fields: - id - source_id - external_id - url - title - text -
published_at - collected_at - language - media_url - status

Status values: - new - processed - rejected - duplicate

------------------------------------------------------------------------

## 4.4 Normalization

Cleaning steps: - remove HTML - normalize whitespace - remove tracking
parameters - unify encoding - extract main article text

Libraries: - trafilatura - BeautifulSoup

------------------------------------------------------------------------

## 4.5 Filtering

Filtering rules include:

-   topic matching
-   language rules
-   blacklist words
-   allowed sources

Rules configurable via admin panel.

------------------------------------------------------------------------

## 4.6 Deduplication

Three levels:

### Exact duplicates

Same URL or identical content hash.

### Near duplicates

Title similarity (RapidFuzz).

### Semantic duplicates

Embeddings + cosine similarity.

Duplicates grouped into duplicate groups.

------------------------------------------------------------------------

## 4.7 Canonical News Item

Table: canonical_items

Fields: - id - headline - summary - body - primary_source -
supporting_sources - status - created_at

------------------------------------------------------------------------

## 4.8 AI Processing

AI used for: - headline generation - summary generation - article
rewrite - tag suggestion - topic classification

Rules: AI must NOT: - invent facts - change names - change numbers - add
opinions

------------------------------------------------------------------------

## 4.9 AI Provider Abstraction

Supported providers: - Gemini - OpenAI - OpenRouter

System must allow switching providers.

------------------------------------------------------------------------

## 4.10 Moderation System

Statuses: - draft - pending_review - approved - rejected - scheduled -
published

Moderators can: - edit rewritten text - approve - reject - schedule
publishing

------------------------------------------------------------------------

## 4.11 Publishing System

### Website

Fields: - slug - headline - body - tags - categories - publish_date

### Telegram

Stored fields: - telegram_message_id - channel_id - publish_status -
publish_time

------------------------------------------------------------------------

# 5. Admin Panel

Sections:

Dashboard - collected news - duplicates detected - pending moderation -
published articles - system errors

Sources - add telegram channel - add rss feed - activate/deactivate
source - assign topic - set priority

Raw News - source - title - preview - timestamp - duplicate status

Canonical News - original sources - AI rewrite - similarity info

Moderation Queue Actions: - approve - reject - edit - schedule - publish

Publishing History - website posts - telegram posts - publish errors

Settings - collection frequency - AI provider - publishing rules

------------------------------------------------------------------------

# 6. User Management

Roles: - Admin - Moderator - Editor

Permissions: - manage sources - approve content - publish content

------------------------------------------------------------------------

# 7. Security Requirements

System must implement:

-   secure authentication
-   role-based access control
-   CSRF protection
-   rate limiting
-   input validation
-   secrets stored in environment variables

------------------------------------------------------------------------

# 8. Logging and Observability

Logs must include:

-   collection events
-   processing events
-   publishing events
-   user actions

------------------------------------------------------------------------

# 9. Background Processing

Celery workers handle:

-   collectors
-   processing pipeline
-   rewrite tasks
-   publishing
-   retry jobs

Retries must use exponential backoff.

------------------------------------------------------------------------

# 10. Testing

Testing framework: pytest

Test types: - unit tests - integration tests - API tests

------------------------------------------------------------------------

# 11. Deployment

Docker services:

-   backend
-   frontend
-   postgres
-   redis
-   worker

Docker Compose must allow full local deployment.

------------------------------------------------------------------------

# 12. Repository Structure

news-platform/

backend/ app/ api/ core/ models/ services/ workers/ pipelines/ auth/
moderation/ publishing/

frontend/ public-site/ admin-panel/

infrastructure/ docker/ scripts/

tests/

docs/ TECH_SPEC.md

------------------------------------------------------------------------

# 13. Scalability

System must support:

-   horizontal scaling of workers
-   high news throughput
-   AI cost optimization

------------------------------------------------------------------------

# 14. Future Extensions

Possible features:

-   semantic clustering
-   automatic topic detection
-   SEO optimization
-   analytics dashboard
-   multi-language publishing

------------------------------------------------------------------------

# 15. Success Criteria

System must:

-   collect news from 10+ sources
-   detect duplicates
-   generate AI rewrites
-   support moderation
-   publish to website
-   publish to Telegram
