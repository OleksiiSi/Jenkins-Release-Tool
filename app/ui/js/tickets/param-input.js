import { paramInputRowTemplate } from '../templates.js';

export function renderParamInput(parameterDefinition, value, onChange) {
    switch (parameterDefinition.type) {
        case 'boolean': {
            const input = document.createElement('input');

            input.type = 'checkbox';
            input.checked = value === 'true';
            input.onchange = () => onChange(input.checked ? 'true' : 'false');

            return input;
        }

        case 'dropdown': {
            const select = document.createElement('select')
            select.className = 'settings-input';

            const blankOption = document.createElement('option');
            blankOption.value = '';
            blankOption.textContent = '— select —';

            select.appendChild(blankOption);

            for (const optionValue of parameterDefinition.options || []) {
                const option = document.createElement('option');

                option.value = optionValue;
                option.textContent = optionValue;

                select.appendChild(option);
            }

            select.value = value;
            select.onchange = () => onChange(select.value);
            return select;
        }

        case 'string': {
            const input = document.createElement('input');
            input.type = 'text';
            input.className = 'branch-input';
            input.value = value;
            input.oninput = () => onChange(input.value);
            return input;
        }

        default:
            throw new Error(`renderParamInput: unknown parameter definition type "${parameterDefinition.type}"`);
    }
}

export function renderParamInputList(container, defs, valueStore, onAnyChange) {
    container.innerHTML = '';

    for (const parameterDefinition of defs) {
        const row = paramInputRowTemplate.content.firstElementChild.cloneNode(true);
        const label = row.querySelector('label');
        const slot = row.querySelector('.param-input-slot');

        label.textContent = parameterDefinition.name;

        const defaultValue = parameterDefinition.type === 'boolean' ? 'false' : '';
        valueStore[parameterDefinition.name] = defaultValue;

        const inputEl = renderParamInput(parameterDefinition, defaultValue, (newValue) => {
            valueStore[parameterDefinition.name] = newValue;
            onAnyChange();
        });

        slot.appendChild(inputEl);
        container.appendChild(row);
    }
}
