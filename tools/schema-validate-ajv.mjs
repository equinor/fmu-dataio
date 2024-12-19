#!/usr/bin/env node

import Ajv2020 from "ajv/dist/2020.js"
import addFormats from "ajv-formats";
import fs from "fs/promises";
import path from "path";
import { fileURLToPath } from "url";

const ajv = new Ajv2020({ strict: false, discriminator: true });
addFormats(ajv);

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const GREEN = "\x1b[32m";
const RED = "\x1b[31m";
const YELLOW = "\x1b[93m";
const NC = "\x1b[0m";
const BOLD = "\x1b[1m";
const SUCCESS = `[${BOLD}${GREEN}✔${NC}]`;
const FAILURE = `[${BOLD}${RED}✖${NC}]`;
const INFO = `[${BOLD}${YELLOW}+${NC}]`;

async function loadJson(filePath) {
  try {
    const fullPath = path.resolve(filePath);
    const fileContent = await fs.readFile(fullPath, "utf-8");
    return JSON.parse(fileContent);
  } catch (err) {
    console.error(`${FAILURE} Error reading file at ${filePath}: ${err.message}`);
    process.exit(1);
  }
}

async function validateSchema(schemaPath) {
  try {
    const schema = await loadJson(schemaPath); 
    const validate = ajv.compile(schema); 
    console.log(`${SUCCESS} Schema is valid: ${schemaPath}`);
    return validate;
  } catch (err) {
    console.error(`${FAILURE} Schema is invalid: ${schemaPath}`);
    console.error(`    ${INFO} Reason: ${err.message}`);
    return false;
  }
}

async function findJsonFiles(dir) {
  let results = [];
  const entries = await fs.readdir(dir, { withFileTypes: true });

  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      results = results.concat(await findJsonFiles(fullPath));
    } else if (entry.isFile() && entry.name.endsWith(".json")) {
      results.push(fullPath);
    }
  }

  return results;
}

async function validateSchemasInDirectory(dirPath) {
  const schemaFiles = await findJsonFiles(dirPath);

  if (schemaFiles.length === 0) {
    console.log(`${INFO} No JSON schema files found in directory: ${dirPath}`);
    return;
  }

  let shouldFail = false;
  console.log(`${INFO} Found ${schemaFiles.length} JSON schema file(s) in directory: ${dirPath}`);
  for (const schemaPath of schemaFiles) {
    const isValid = await validateSchema(schemaPath);
    if (!isValid) {
        shouldFail = true;
    }
  }
  if (shouldFail) {
    process.exit(1);
  }
}

const directory = process.argv[2];

if (!directory) {
  console.error("Usage: validate-schema-ajv.mjs <directory>");
  process.exit(1);
}

validateSchemasInDirectory(directory).catch((err) => {
  console.error(`${FAILURE} Unknown error: ${err.message}`);
  process.exit(1);
});
