import { createElement } from "./utils.js";

class Docs {
    #schemas;

    constructor(schemas) {
        this.#schemas = schemas;
    }

    generate() {
        this.#populateTabs();
        this.#populateToc(this.#schemas[0]);
        this.#populateDocs(this.#schemas[0]);
    }

    #populateTabs() {
        const navbar = document.getElementById("navbar");
        navbar.innerHTML = "";

        for (const schema of this.#schemas) {
            const navBarItem = createElement("div", {
                innerHTML: schema.title,
                className: "navbar-item",
            });

            navBarItem.addEventListener("click", () => {
                this.#populateToc(schema);
                this.#populateDocs(schema);
                document.querySelectorAll(".navbar-item").forEach((el) => {
                    el.classList.remove("navbar-item-selected");
                });

                navBarItem.classList.add("navbar-item-selected");
            });

            navbar.appendChild(navBarItem);
        }

        document
            .getElementsByClassName("navbar-item")[0]
            .classList.add("navbar-item-selected");
    }

    #populateToc(schema) {
        const toc = document.getElementById("toc-content");
        toc.innerHTML = "";

        for (const { propPath } of schema.props) {
            const container = createElement("div");
            const link = createElement("a", {
                className: "toc-link",
                href: `#${propPath}`,
                text: propPath,
            });

            toc.appendChild(container);
            container.appendChild(link);
        }
    }

    #populateDocs(schema) {
        const content = document.getElementById("content");
        content.innerHTML = "";

        for (const { propPath, def } of schema.props) {
            this.#populateProp(propPath, def);
        }
    }

    #populateProp = (propPath, def, parentEl = null, name = null) => {
        const container = createElement("div", {
            className: "prop-container",
        });

        const header = createElement("div", {
            className: "prop-header",
            id: propPath,
        });

        const title = createElement("div", {
            className: "prop-title",
            innerHTML:
                name || `${propPath} ${def?.title ? ` (${def.title})` : ""}`,
        });

        const type = createElement("div", {
            className: "prop-type",
            innerHTML: def?.type,
        });

        const body = createElement("div", { className: "prop-body" });

        if (!def) {
            body.appendChild(
                createElement("p", {
                    innerHTML: "No definition found in schema",
                })
            );
        }

        if (def?.description) {
            body.appendChild(
                createElement("div", {
                    className: "prop-description",
                    innerHTML: def.description,
                })
            );
        }

        if (def?.type === "array") {
            this.#populateProp(propPath, def?.items, body, "Items");
        }

        if (def?.type === "object" && def?.properties) {
            for (const [childProp, childDef] of Object.entries(
                def.properties
            )) {
                this.#populateProp(childProp, childDef, body);
            }
        }

        if (def?.examples) {
            const exContent = createElement("div", {
                className: "prop-example",
            });

            for (const example of def.examples) {
                exContent.appendChild(
                    createElement("div", { innerHTML: example })
                );
            }

            body.appendChild(
                createElement("div", {
                    className: "prop-example-title",
                    innerHTML: "Example:",
                })
            );
            body.appendChild(exContent);
        }

        header.appendChild(title);
        header.appendChild(type);
        container.appendChild(header);
        container.appendChild(body);

        if (parentEl) {
            parentEl.appendChild(container);
        } else {
            const content = document.getElementById("content");
            content.appendChild(container);
        }
    };
}

export default Docs;
