# Project Configuration
**Title:** Design and Implementation of a Privacy-Preserving Medical Diagnosis System using Federated Learning  
**Author:** Daniel Popoola
**Domain:** Machine Learning, Cyber-Security, Healthcare Informatics  
**Keywords:** Federated Learning, Privacy-Preserving AI, Medical Image Analysis, Distributed Systems, Data Security, CNN

# Problem Statement
In the modern healthcare landscape, deep learning models have shown immense potential in diagnosing diseases from medical images (like X-rays or MRIs). However, training these models requires massive, diverse datasets which are often siloed across different hospitals. The current situation forces a choice between two poor options: either training "weak" models on small local datasets or moving sensitive patient data to a central server for training.

Moving data to a central location creates significant pain points. It exposes sensitive patient information to potential data breaches and often violates strict privacy regulations such as HIPAA (USA) or GDPR (EU). Because of these legal and ethical barriers, hospitals are reluctant to share data, leading to a "data island" problem where life-saving AI tools cannot be effectively trained.

This problem affects medical researchers, healthcare providers, and ultimately patients, who may receive less accurate diagnoses due to under-trained models. Without a way to bridge these data islands while maintaining absolute privacy, the progress of AI in clinical settings will remain stagnant.

# Your Solution
This project implements a Federated Learning (FL) framework that allows multiple healthcare institutions to collaboratively train a shared global model without ever exchanging raw patient data. The system consists of a central aggregation server and multiple client nodes (representing different hospitals).

The system functions by sending the current global model weights to the participating clients. Each client trains the model on its own local, private data and then sends only the updated model weights (gradients) back to the central server. The server aggregates these updates (using the Federated Averaging algorithm) to improve the global model and redistribute it.

Key features include:
- Decentralized Training: Local data never leaves the hospital premises.
- Secure Aggregation: An implementation of the FedAvg algorithm to merge model updates.
- Real-time Monitoring Dashboard: A web interface to track the training progress and model accuracy across all participating nodes.

# Why This Approach
The Federated Learning approach was chosen because it directly solves the "privacy vs. utility" trade-off. Unlike traditional Centralized Learning, which requires a single point of failure (the central database), FL distributes the risk. Even if the central server is compromised, it only contains model weights—not actual patient images.

Alternatives considered included Differential Privacy and Homomorphic Encryption. While these provide strong security, they often introduce significant "noise" into the data or incur massive computational overhead that makes them impractical for complex image classification tasks on undergraduate-level hardware. FL provides the most balanced trade-off between high model accuracy and regulatory compliance.

One trade-off made was the increased communication overhead. Since model weights are transmitted back and forth, the system is more dependent on network stability than a centralized system. However, this is a necessary cost to ensure data remains strictly local.

# System Architecture
The system follows a Client-Server architecture designed for distributed training.

- **Main Components:**
    - **Global Aggregator (Server):** Manages the training rounds and performs weight averaging.
    - **Local Trainers (Clients):** Independent nodes that hold local datasets and perform computation.
    - **Storage Layer:** Local SQLite databases for clients to manage metadata and a central repository for the global model.
    - **API Gateway:** Handles communication between server and clients.

- **Design Patterns:**
    - **Observer Pattern:** The server monitors the status of clients to start aggregation once enough updates are received.
    - **Strategy Pattern:** Allows switching between different aggregation algorithms (e.g., FedAvg vs. FedProx).

**Tech Stack:**
- **Frontend:** React with Chart.js (for monitoring training metrics)
- **Backend:** Python with Flask
- **Machine Learning:** PyTorch and Flower (FL Framework)
- **Database:** PostgreSQL (for training logs)
- **Communication:** WebSockets for real-time model updates

# Implementation Highlights
- **Federated Averaging (FedAvg):** The core logic that calculates the weighted average of client updates based on their local dataset sizes.
- **Model Quantization:** Implemented to reduce the size of the weights being transmitted, optimizing performance for lower-bandwidth environments.
- **Client Selection Logic:** A custom algorithm to ensure only clients with sufficient battery/CPU resources are selected for each training round.

# Test Results
- **Model Performance:** The global federated model achieved 92.4% accuracy on the test set, compared to 94.1% for a centralized model (less than 2% "privacy penalty").
- **Privacy Verification:** Packet sniffing (using Wireshark) confirmed that zero raw image data was transmitted over the network.
- **Scalability:** System successfully synchronized 5 concurrent client nodes.
- **Network Efficiency:** Quantization reduced weight update sizes by 65% with only a 0.4% loss in accuracy.

# Dependencies
**Backend & ML:**
- Python 3.10+
- Flower (flwr) 1.5.0
- PyTorch 2.1.0
- NumPy 1.24.0

**Frontend & Monitoring:**
- Node.js 18
- React 18
- Socket.io (for real-time updates)

**Infrastructure:**
- Docker (for containerizing client nodes)
- FastAPI (for the communication layer)

# Data & Testing Strategy
**Data Source:**
- **Kaggle Chest X-Ray Dataset (Pneumonia):** This public dataset was partitioned into five non-IID (Independent and Identically Distributed) subsets to simulate five different hospitals with varying types of patients.

**Testing Approach:**
- **Unit Tests:** Verified the data-loading pipelines and local training functions (Pytest).
- **Integration Tests:** Tested the WebSocket connection between the Flower server and clients.
- **Accuracy Benchmarking:** Compared the FL model's convergence rate against a standard centrally-trained CNN.

# Limitations You Faced
**Technical Constraints:**
- "Wanted to implement Secure Multi-Party Computation (SMPC) for the aggregation step, but the computational cost was too high for standard laptop CPUs."
- "Limited the number of clients to 5 due to local RAM constraints during simulation."

**Design Trade-offs:**
- "Chose a synchronous update strategy for simplicity, meaning the server waits for the slowest client before proceeding to the next round (Straggler problem)."
- "Used a simple CNN (ResNet-18) rather than a larger Transformer model to ensure training could finish within reasonable timeframes on undergraduate hardware."