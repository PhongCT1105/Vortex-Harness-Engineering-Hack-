## ADDED Requirements

### Requirement: Authenticated client construction
The module SHALL expose an `authenticate()` function that loads env vars via `python-dotenv`, reads `JUA_KEY_ID` and `JUA_SECRET`, and returns an authenticated Jua SDK client. It SHALL raise a `ValueError` with a message naming the missing variable if either is absent or empty.

#### Scenario: Both credentials present
- **WHEN** `JUA_KEY_ID` and `JUA_SECRET` are set in the environment
- **THEN** `authenticate()` returns a valid Jua SDK client without raising

#### Scenario: Missing JUA_KEY_ID
- **WHEN** `JUA_KEY_ID` is not set or is empty
- **THEN** `authenticate()` raises `ValueError` with a message identifying `JUA_KEY_ID` as missing

#### Scenario: Missing JUA_SECRET
- **WHEN** `JUA_SECRET` is not set or is empty
- **THEN** `authenticate()` raises `ValueError` with a message identifying `JUA_SECRET` as missing

### Requirement: HTTP error translation
The module SHALL catch HTTP errors from the Jua API (400, 401, 402, 403) and re-raise them as exceptions with readable messages that identify the status code and its meaning.

#### Scenario: 401 Unauthorized
- **WHEN** the Jua API returns HTTP 401
- **THEN** an exception is raised with a message indicating invalid or missing credentials

#### Scenario: 403 Forbidden
- **WHEN** the Jua API returns HTTP 403
- **THEN** an exception is raised with a message indicating the account lacks access to the requested resource

#### Scenario: 402 Payment Required
- **WHEN** the Jua API returns HTTP 402
- **THEN** an exception is raised with a message indicating quota or billing issue

#### Scenario: 400 Bad Request
- **WHEN** the Jua API returns HTTP 400
- **THEN** an exception is raised with a message indicating a malformed request
