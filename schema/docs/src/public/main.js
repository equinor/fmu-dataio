import Schema from "./scripts/Schema.js";
import Docs from "./scripts/Docs.js";

//const schemaUrl = "https://main-fmu-schemas-dev.radix.equinor.com/schemas/0.8.0/fmu_results.json";
const schemaUrl = "./fmu_results_080.json";

window.addEventListener("load", () => {
    fetch(schemaUrl)
        .then((response) => response.json())
        .then((schema) => {
            const mySchema = new Schema(schema);
            const myDocs = new Docs(mySchema.getSubSchemas());
            myDocs.generate();
        });
});
