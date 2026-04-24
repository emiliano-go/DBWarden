# Introduction

DBWarden is a SQL-first migration tool for Python projects that use SQLAlchemy.

It helps you generate, review, apply, and rollback migrations with explicit SQL files.

## What DBWarden Is

- A migration workflow centered on readable SQL files
- A CLI for generating and applying migrations safely
- A multi-database migration system with lock protection

## What DBWarden Is Not

- An ORM replacement
- A hidden auto-migration engine that changes schema implicitly
- A deployment platform

## Who Uses DBWarden

Teams that value SQL review as part of their deployment flow, projects with multiple databases needing consistent migration execution.

## Core Ideas

- SQL is the source of truth
- Upgrade and rollback are defined together
- Safety features (locking, checksums, status) are built in

## Navigation

- Next: [Installation](../installation.md)
