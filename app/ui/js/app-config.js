export let generalParametersConfig = [];
export let generalEnvironmentsConfig = [];
export let jobsConfig = {};

export function setAppConfig(settings) {
    generalParametersConfig = settings.jobs_config.general.parameters;
    generalEnvironmentsConfig = settings.jobs_config.general.environments;
    jobsConfig = settings.jobs_config.job_specific;
}
