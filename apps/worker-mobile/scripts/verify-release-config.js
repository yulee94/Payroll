const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const appJsonPath = path.join(root, 'app.json');
const configPath = path.join(root, 'app.config.js');
const reviewPath = path.join(root, 'review-assets', 'app-review-checklist.json');
const app = require(appJsonPath).expo;
const dynamicConfig = require(configPath)();
const review = JSON.parse(fs.readFileSync(reviewPath, 'utf8'));

const requiredFiles = [
  app.icon,
  app.splash && app.splash.image,
  app.android && app.android.adaptiveIcon && app.android.adaptiveIcon.foregroundImage,
  review.assets && review.assets.app_icon,
  review.assets && review.assets.splash,
  'review-assets/screenshots/ios/01-login.png',
  'review-assets/screenshots/ios/02-attendance.png',
  'review-assets/screenshots/ios/03-payroll.png',
  'review-assets/screenshots/android/01-login.png',
  'review-assets/screenshots/android/02-attendance.png',
  'review-assets/screenshots/android/03-payroll.png',
];

const failures = [];
for (const rel of requiredFiles) {
  if (!rel) {
    failures.push('missing asset path in config');
    continue;
  }
  const clean = String(rel).replace(/^\.\//, '');
  if (!fs.existsSync(path.join(root, clean))) {
    failures.push(`missing file: ${clean}`);
  }
}

const apiUrls = dynamicConfig.extra && dynamicConfig.extra.apiUrls;
for (const key of ['development', 'staging', 'production']) {
  if (!apiUrls || !apiUrls[key] || !/^https:\/\//.test(apiUrls[key])) {
    failures.push(`missing https ${key} API URL`);
  }
}
for (const key of ['DEV_API_URL', 'STAGING_API_URL', 'PROD_API_URL']) {
  if (!dynamicConfig.extra || !dynamicConfig.extra[key] || !/^https:\/\//.test(dynamicConfig.extra[key])) {
    failures.push(`missing ${key}`);
  }
}
if (!dynamicConfig.ios?.bundleIdentifier?.includes('.dev')) failures.push('development bundle identifier must be environment-specific');
if (!dynamicConfig.android?.package?.includes('.dev')) failures.push('development Android package must be environment-specific');
for (const key of ['test_account', 'test_branch_data', 'required_urls', 'support_contact', 'app_description', 'permission_usage_reasons']) {
  if (!review[key]) failures.push(`review checklist missing ${key}`);
}
if (!app.ios?.infoPlist?.NSLocationWhenInUseUsageDescription) failures.push('iOS location permission reason missing');
if (!app.plugins?.some((plugin) => Array.isArray(plugin) && plugin[0] === 'expo-notifications')) failures.push('expo-notifications plugin missing');

if (failures.length) {
  console.error('Mobile release config check failed:');
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log('Mobile release config check passed.');
