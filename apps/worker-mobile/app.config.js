const base = require('./app.json').expo;

const ENVIRONMENTS = ['development', 'staging', 'production'];

function pickEnvironment() {
  const value = process.env.APP_ENV || process.env.EAS_BUILD_PROFILE || base.extra?.appEnvironment || 'development';
  return ENVIRONMENTS.includes(value) ? value : 'development';
}

function apiUrls() {
  return {
    development: process.env.DEV_API_URL || base.extra?.apiUrls?.development || 'https://dev.mobile-api.bitween.example',
    staging: process.env.STAGING_API_URL || base.extra?.apiUrls?.staging || 'https://staging.mobile-api.bitween.example',
    production: process.env.PROD_API_URL || base.extra?.apiUrls?.production || 'https://mobile-api.bitween.example',
  };
}

module.exports = () => {
  const appEnvironment = pickEnvironment();
  const urls = apiUrls();
  const profileSuffix = appEnvironment === 'production' ? '' : ` ${appEnvironment.toUpperCase()}`;
  const identifiers = {
    development: {
      scheme: 'bitween-worker-dev',
      iosBundleIdentifier: 'com.bitween.worker.dev',
      androidPackage: 'com.bitween.worker.dev',
    },
    staging: {
      scheme: 'bitween-worker-staging',
      iosBundleIdentifier: 'com.bitween.worker.staging',
      androidPackage: 'com.bitween.worker.staging',
    },
    production: {
      scheme: base.scheme,
      iosBundleIdentifier: base.ios?.bundleIdentifier || 'com.bitween.worker',
      androidPackage: base.android?.package || 'com.bitween.worker',
    },
  }[appEnvironment];

  return {
    ...base,
    name: `${base.name}${profileSuffix}`,
    scheme: identifiers.scheme,
    ios: {
      ...base.ios,
      bundleIdentifier: identifiers.iosBundleIdentifier,
    },
    android: {
      ...base.android,
      package: identifiers.androidPackage,
    },
    extra: {
      ...base.extra,
      appEnvironment,
      apiUrls: urls,
      mobileApiBaseUrl: urls[appEnvironment],
      DEV_API_URL: urls.development,
      STAGING_API_URL: urls.staging,
      PROD_API_URL: urls.production,
    },
  };
};
