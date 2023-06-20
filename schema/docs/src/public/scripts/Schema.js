class Schema {
    #schema;
    #defs;

    constructor(schema) {
        this.#schema = schema;
        this.#defs = schema?.$defs || schema?.definitions;
    }

    // get path to reference
    #getRefPath(ref) {
        return ref
            .replace("#/$defs/", "")
            .replace("#/definitions/", "")
            .replaceAll("/", ".")
            .replaceAll(".properties.", ".");
    }

    // get a property definition
    #getPropDef(defs, path) {
        let def = path.split(".").reduce((prev, curr) => {
            return prev?.properties?.[curr] || prev?.[curr];
        }, defs);

        if (def?.properties) {
            for (const [prop, propDef] of Object.entries(def.properties)) {
                if (propDef.$ref) {
                    def.properties[prop] = this.#getPropDef(
                        this.#defs,
                        this.#getRefPath(propDef.$ref)
                    );
                }
            }
        }

        if (def?.items?.properties) {
            for (const [prop, propDef] of Object.entries(
                def.items.properties
            )) {
                if (propDef.$ref) {
                    def.items.properties[prop] = this.#getPropDef(
                        this.#defs,
                        this.#getRefPath(propDef.$ref)
                    );
                }
            }
        }

        if (def?.$ref) {
            def = this.#getPropDef(this.#defs, this.#getRefPath(def.$ref));
        }

        if (def?.items?.$ref) {
            def.items = this.#getPropDef(
                this.#defs,
                this.#getRefPath(def.items.$ref)
            );
        }

        return def;
    }

    // get all properties in an "oneOf" section
    #handleOneOf(def) {
        let newDef = { properties: def?.properties || {} };

        for (const one of def.oneOf) {
            if (one.properties) {
                for (const [prop, propDef] of Object.entries(one.properties)) {
                    if (propDef.$ref) {
                        newDef.properties[prop] = this.#getPropDef(
                            one.properties,
                            prop
                        );
                    } else {
                        newDef.properties[prop] = propDef;
                    }
                }
            } else if (one.allOf) {
                newDef.properties = {
                    ...newDef?.properties,
                    ...this.#handleAllOf(one).properties,
                };
            }
        }

        return newDef;
    }

    // get all properties in an "allOf" section
    #handleAllOf(def) {
        let newDef = { properties: def?.properties || {} };

        for (const one of def.allOf) {
            if (one.properties) {
                for (const [prop, propDef] of Object.entries(one.properties)) {
                    if (propDef.$ref) {
                        newDef.properties[prop] = this.#getPropDef(
                            one.properties,
                            prop
                        );
                    } else {
                        newDef.properties[prop] = propDef;
                    }
                }
            } else if (one.oneOf) {
                newDef.properties = {
                    ...newDef?.properties,
                    ...this.#handleOneOf(one).properties,
                };
            }
        }

        return newDef;
    }

    // Creates a flat list of props from a schema
    #extractProps(schema, currentDefs = null, path = "", props = []) {
        let newProps = [...props];

        for (const [prop] of Object.entries(currentDefs || schema)) {
            const propPath = `${path}${path ? "." : ""}${prop}`;
            let def = this.#getPropDef(schema, propPath);

            if (def?.oneOf) {
                def = this.#handleOneOf(def);
            }

            if (def?.allOf) {
                def = this.#handleAllOf(def);
            }

            if (def?.properties) {
                newProps = this.#extractProps(
                    schema,
                    def.properties,
                    propPath,
                    newProps
                );
            } else {
                newProps.push({
                    propPath,
                    def,
                });
            }
        }

        return newProps;
    }

    // merge two property definitions
    #mergeDefs(defOne, defTwo) {
        let properties = {};
        let rest = {};

        for (let def of [defOne, defTwo]) {
            if (def?.$ref) {
                const refPath = this.#getRefPath(def?.$ref);
                def = this.#getPropDef(this.#defs, refPath);
            }

            if (def?.properties) {
                properties = { ...properties, ...def.properties };
            }

            if (def?.oneOf) {
                properties = {
                    ...properties,
                    ...this.#handleOneOf(def)?.properties,
                };
            }

            if (def?.allOf) {
                properties = {
                    ...properties,
                    ...this.#handleAllOf(def)?.properties,
                };
            }

            for (const prop of [
                "type",
                "examples",
                "title",
                "description",
                "items",
                "enum",
                "const",
            ]) {
                if (def?.[prop]) {
                    rest[prop] = def[prop];
                }
            }
        }

        return {
            ...rest,
            ...(Object.keys(properties).length > 0 && { properties }),
        };
    }

    // get list of subschemas in schema
    getSubSchemas() {
        return this.#schema.oneOf.map((subSchema) => {
            const propList = [
                ...this.#schema.required,
                ...(subSchema?.required ? subSchema.required : []),
            ];

            const mergedSchema = propList.reduce((prev, curr) => {
                const base = this.#schema.properties?.[curr];
                const sub = subSchema.properties?.[curr];

                return { ...prev, [curr]: this.#mergeDefs(base, sub) };
            }, {});

            return {
                title: subSchema?.title || subSchema?.$comment || "no title",
                props: this.#extractProps(mergedSchema),
            };
        });
    }
}

export default Schema;
