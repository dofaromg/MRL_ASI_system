// origin_signature: MrLiouWord
'use strict';
const fs = require('node:fs');
const path = require('node:path');
const { randomBytes, createHash } = require('node:crypto');

function provision(directory, id, quota, ownerGrantRef) {
  if (!path.isAbsolute(directory) || !/^[a-zA-Z0-9_-]{1,64}$/.test(id) ||
      !Number.isSafeInteger(quota) || quota < 0 || typeof ownerGrantRef !== 'string' || !ownerGrantRef.trim()) {
    throw new Error('Usage: node MRL_ProvisionAccount.cjs ABSOLUTE_DIRECTORY ACCOUNT_ID MONTHLY_QUOTA OWNER_GRANT_REFERENCE');
  }
  fs.mkdirSync(directory, { recursive: true, mode: 0o700 });
  const keyFile = path.join(directory, `${id}.key`);
  const configFile = path.join(directory, 'accounts.json');
  const token = randomBytes(32).toString('hex');
  const account = { id, keyHash: createHash('sha256').update(token).digest('hex'), monthlyQuota: quota, enabled: true, ownerGrantRef };
  fs.writeFileSync(keyFile, token + '\n', { mode: 0o600, flag: 'wx' });
  try { fs.writeFileSync(configFile, JSON.stringify([account], null, 2) + '\n', { mode: 0o600, flag: 'wx' }); }
  catch (error) { fs.unlinkSync(keyFile); throw error; }
  return { configFile, keyFile };
}
if (require.main === module) {
  const [directory, id, quota, ownerGrantRef] = process.argv.slice(2);
  console.log(JSON.stringify(provision(directory || '', id || '', Number(quota), ownerGrantRef), null, 2));
}
module.exports = { provision };
