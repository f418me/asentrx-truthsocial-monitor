> **Note:** This service is a component of the [aSentrX Project](https://github.com/f418me/aSentrX). Please see the main repository for a complete architectural overview.

# aSentrix Truth Social Monitor

This service monitors a specific user account on Truth Social for new posts ("statuses"). When a new status is detected, it is sent to a configurable webhook URL for further processing by another service (e.g., the `asentrx-trade-decision-engine`).

## Features

*   **Targeted User Monitoring**: Monitors a specific Truth Social username for new posts.
*   **Configurable Interval**: Checks for new statuses every X seconds (configurable via `.env`).
*   **Stateful Processing**: Keeps track of the last processed status ID to avoid sending duplicates.
*   **JSON Payload**: Sends a structured JSON object to a specified webservice URL.
*   **Error Logging**: Logs messages for successful and failed operations.
*   **Containerized**: Ready for deployment using Docker, Docker Compose, and Fly.io.
*   **Poetry**: Manages Python dependencies efficiently.

## Prerequisites

Before you begin, ensure you have the following installed:

*   **Git**: For cloning the repository.
*   **Docker**: [Install Docker Desktop](https://www.docker.com/products/docker-desktop)
*   **Docker Compose**: Usually comes bundled with Docker Desktop.

## Setup and Running

Follow these steps to get the `asentrx-truthsocial-monitor` up and running:

### 1. Clone the Repository

First, clone this repository to your local machine:

```bash
git clone https://github.com/f418me/asentrx-truthsocial-monitor.git
cd asentrx-truthsocial-monitor
```

### 2. Configure Environment Variables

Create a `.env` file by copying the example file:

```bash
cp .env-example .env
```

Now, edit the `.env` file and provide the necessary values:

*   `WEBSERVICE_URL`: The URL of the endpoint that will receive the notifications (e.g., the `/notify` endpoint of the `asentrx-trade-decision-engine`).
*   `FLY_PUBLIC_IP`: The public IP address of the machine or container running this service. This is used to identify the source of the notification.
*   `TRUTHSOCIAL_USERNAME`: Your Truth Social login username.
*   `TRUTHSOCIAL_PASSWORD`: Your Truth Social login password.
*   `TARGET_USERNAME`: The Truth Social user you want to monitor (e.g., "realDonaldTrump").
*   `FETCH_INTERVAL_SECONDS`: The interval in seconds to check for new posts.
*   `LOG_LEVEL`: The logging level (e.g., `INFO`, `DEBUG`).

### 3. Build and Run with Docker

You can build and run the service using Docker Compose:

```bash
docker-compose up --build
```

The service will start, log in to Truth Social, and begin monitoring the target user for new posts.