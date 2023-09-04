export const createElement = (type, config = {}) => {
    const el = document.createElement(type);

    for (const [key, value] of Object.entries(config)) {
        if (key === "children") {
            for (const child of value) {
                el.appendChild(child);
            }
        } else {
            el[key] = value;
        }
    }

    return el;
};
