// Ambient type declarations for the `window.pywebview.api` bridge injected
// at runtime by pywebview. Mirrors api.py's `Api` class method-for-method so
// PyCharm/WebStorm can resolve and autocomplete `window.pywebview.api.*`
// calls in app.js. Not referenced by index.html - editor tooling only.

interface ParameterDef {
    name: string;
    type: "string" | "boolean" | "dropdown";
    options?: string[];
    is_unique_between_tickets?: boolean;
}

interface EnvironmentDef {
    name: string;
    promotion_process: string;
}

interface JobConfig {
    parameters: ParameterDef[];
    environments: EnvironmentDef[];
}

interface JobsConfig {
    general: { parameters: ParameterDef[]; environments: EnvironmentDef[] };
    job_specific: Record<string, JobConfig>;
}

interface Settings {
    jenkins: { base_url: string; username: string };
    notification_connectors: { teams: { webhook_url: string } };
    job_run_config: { poll_interval_minutes: number; max_retries: number };
    jobs_config: JobsConfig;
}

interface JobRequest {
    job_name: string;
    parameters: Record<string, string>;
    environments: Record<string, string>;
}

interface TicketRequest {
    ticket_id: string;
    jobs: JobRequest[];
}

interface RunAllResult {
    errors: string[];
    token_missing: boolean;
}

interface LogEntryJson {
    timestamp: string;
    level: "info" | "ok" | "fail" | "warn";
    message: string;
}

interface TokenStatus {
    saved: boolean;
}

interface ConnectionStatus {
    jenkins: boolean;
    teams: boolean;
}

interface PywebviewApi {
    run_all(ticketRequests: TicketRequest[]): Promise<RunAllResult>;
    get_new_logs(): Promise<LogEntryJson[]>;
    is_runner_finished(): Promise<boolean>;
    get_settings(): Promise<Settings>;
    save_settings(data: Settings): Promise<void>;
    reset_settings(): Promise<Settings>;
    save_token(token: string): Promise<TokenStatus>;
    get_token_status(): Promise<TokenStatus>;
    get_connection_status(): Promise<ConnectionStatus>;
    restart_app(): Promise<void>;
    exit_app(): Promise<void>;
}
