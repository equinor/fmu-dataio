#!/usr/bin/env node

/**
 * Script to validate the metadata files inside the examples directory 
 * against local schemas using AJV. The schema version to use is picked up
 * from the metadata field 'version'.
 */

import Ajv2020 from "ajv/dist/2020.js"
import addFormats from "ajv-formats";
import fs from "fs/promises";
import path from "path";
import yaml from "yaml";

const ajv = new Ajv2020({ strict: false, discriminator: true });
addFormats(ajv);

const validatorCache = {}; 

const GREEN = "\x1b[32m";
const RED = "\x1b[31m";
const YELLOW = "\x1b[93m";
const NC = "\x1b[0m";
const BOLD = "\x1b[1m";
const SUCCESS = `[${BOLD}${GREEN}✔${NC}]`;
const FAILURE = `[${BOLD}${RED}✖${NC}]`;
const INFO = `[${BOLD}${YELLOW}+${NC}]`;


async function loadSchema(version, schemasRoot) {
  try {
    const schemaPath = path.join(schemasRoot, version, "fmu_results.json");
    const fileContent = await fs.readFile(schemaPath, "utf-8");
    return JSON.parse(fileContent);
  } catch (err) {
    console.error(`${FAILURE} Error loading schema for version ${version}: ${err.message}`);
    process.exit(1);
  }
}

async function loadYaml(filePath) {
  try {
    const fileContent = await fs.readFile(path.resolve(filePath), "utf-8");
    return yaml.parse(fileContent);
  } catch (err) {
    console.error(`${FAILURE} Error reading YAML at ${filePath}: ${err.message}`);
    process.exit(1);
  }
}

async function validateMetadataFile(yamlPath, schemasRoot) {
  const data = await loadYaml(yamlPath);
  const version = data.version;
  if (!version) {
    console.error(`${FAILURE} No 'version' field found in ${yamlPath}`);
    process.exit(1);
  }

  // Check if validator for this version is already compiled
  let validate = validatorCache[version];
  if (!validate) {
    const schema = await loadSchema(version, schemasRoot);
    validate = ajv.compile(schema);
    validatorCache[version] = validate;
  }

  const valid = validate(data);

  if (valid) {
    console.log(`${SUCCESS} Metadata is valid (schema ${version}): ${yamlPath}`);
    return valid
  } else {
    console.error(`${FAILURE} Metadata is invalid (schema ${version}): ${yamlPath}`);
    console.error(`    ${INFO} Reason:`, ajv.errorsText(validate.errors, {dataVar: ""}));
    return false;
  }
}

async function findYmlFiles(dir) {
  let results = [];
  const entries = await fs.readdir(dir, { withFileTypes: true });

  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      results = results.concat(await findYmlFiles(fullPath));
    } else if (entry.isFile() && entry.name.endsWith(".yml")) {
      results.push(fullPath);
    }
  }

  return results;
}

async function validateMetadataExamplesInDirectory(dirPath, schemasRoot) {
  const metadataFiles = await findYmlFiles(dirPath);

  if (metadataFiles.length === 0) {
    console.log(`${INFO} No JSON schema files found in directory: ${dirPath}`);
    return;
  }

  let shouldFail = false;
  console.log(`${INFO} Found ${metadataFiles.length} Yaml file(s) in directory: ${dirPath}`);
  for (const metadataPath of metadataFiles) {
    const isValid = await validateMetadataFile(metadataPath, schemasRoot);
    if (!isValid) {
        shouldFail = true;
    }
  }
  if (shouldFail) {
    process.exit(1);
  }
}

const exampleDirectory = process.argv[2];
const schemasRoot = process.argv[3];

if (!exampleDirectory) {
  console.error("Usage: examples-validate-ajv.mjs <exampleDirectory> <schemasRoot>");
  process.exit(1);
}

validateMetadataExamplesInDirectory(exampleDirectory, schemasRoot).catch((err) => {
  console.error(`${FAILURE} Unknown error: ${err.message}`);
  process.exit(1);
});
