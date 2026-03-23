import { writeFile } from 'node:fs/promises';

const ZOTERO_GROUP_ID = 5985739;
const PAGE_SIZE = 100;
const MAX_RETRIES = 3;
const RETRY_BASE_DELAY_MS = 1000;
const OUTPUT_PATH = 'files/zotero-items.json';

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function fetchWithRetry(url, options = {}, retries = MAX_RETRIES) {
  let lastError;

  for (let attempt = 1; attempt <= retries; attempt += 1) {
    try {
      const response = await fetch(url, options);

      if (!response.ok) {
        throw new Error(`HTTP ${response.status} ${response.statusText}`);
      }

      return response;
    } catch (error) {
      lastError = error;
      if (attempt < retries) {
        const delay = RETRY_BASE_DELAY_MS * 2 ** (attempt - 1);
        console.warn(`Attempt ${attempt} failed. Retrying in ${delay} ms...`);
        await sleep(delay);
      }
    }
  }

  throw new Error(`Failed after ${retries} attempts: ${lastError?.message ?? 'Unknown error'}`);
}

async function fetchAllZoteroItems() {
  let start = 0;
  let page = 1;
  const allItems = [];

  while (true) {
    const url = `https://api.zotero.org/groups/${ZOTERO_GROUP_ID}/items?format=json&limit=${PAGE_SIZE}&start=${start}`;
    console.log(`Fetching page ${page}: ${url}`);

    const response = await fetchWithRetry(url, {
      headers: {
        Accept: 'application/json'
      }
    });

    const items = await response.json();

    if (!Array.isArray(items)) {
      throw new Error('Unexpected API response: expected JSON array.');
    }

    allItems.push(...items);
    console.log(`  Received ${items.length} items (running total: ${allItems.length})`);

    if (items.length < PAGE_SIZE) {
      break;
    }

    start += PAGE_SIZE;
    page += 1;
  }

  return allItems;
}

async function main() {
  const startedAt = new Date().toISOString();
  console.log(`Started Zotero cache refresh at ${startedAt}`);

  const items = await fetchAllZoteroItems();
  await writeFile(OUTPUT_PATH, `${JSON.stringify(items, null, 2)}\n`, 'utf8');

  const finishedAt = new Date().toISOString();
  console.log(`Wrote ${items.length} items to ${OUTPUT_PATH}`);
  console.log(`Finished Zotero cache refresh at ${finishedAt}`);
}

main().catch((error) => {
  console.error(`Zotero cache refresh failed: ${error.message}`);
  process.exit(1);
});
