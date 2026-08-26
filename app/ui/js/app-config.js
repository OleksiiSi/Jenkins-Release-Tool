// Config loaded once from settings.json at startup (see main.js's init()) -
// effectively read-only afterward. Distinct from session-state.js, which
// holds state that mutates as the user interacts with the app.

export let generalParametersConfig = [];
export let generalEnvironmentsConfig = [];
export let jobsConfig = {};

export function setAppConfig(settings) {
    generalParametersConfig = settings.jobs_config.general.parameters;
    generalEnvironmentsConfig = settings.jobs_config.general.environments;
    jobsConfig = settings.jobs_config.job_specific;
}
