# Android Architecture Documentation

This document describes the architecture, design patterns, and implementation details of the MIA Android application.

## Overview

The MIA Android app follows **MVVM (Model-View-ViewModel)** architecture with **Clean Architecture** principles. The app uses modern Android development practices including Jetpack Compose for UI, Kotlin Coroutines for asynchronous operations, and Hilt for dependency injection.

## Architecture Layers

```
┌─────────────────────────────────────────────────────────────────┐
│                     Presentation Layer                          │
│  ┌─────────────┐  ┌─────────────┐  ┌───────────────────────┐ │
│  │   Screens   │  │  ViewModels │  │  UI State (StateFlow)   │ │
│  │  (Compose)  │──│             │──│                         │ │
│  └─────────────┘  └─────────────┘  └───────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Domain Layer                              │
│  ┌─────────────────┐  ┌───────────────────────────────────────┐│
│  │  Repositories   │  │  Business Logic / Use Cases           ││
│  └─────────────────┘  └───────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Data Layer                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────────┐  │
│  │  Remote  │  │   Local  │  │  BLE     │  │   WebSocket    │  │
│  │   APIs   │  │ Database │  │ Manager  │  │    Client      │  │
│  └──────────┘  └──────────┘  └──────────┘  └────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```
