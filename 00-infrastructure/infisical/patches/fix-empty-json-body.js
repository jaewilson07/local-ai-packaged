/**
 * Infisical Fastify Patch: Fix Empty JSON Body Error
 *
 * This patch overrides Fastify's default application/json content-type parser
 * to accept empty bodies (treating them as empty objects {}).
 *
 * The issue: Infisical's frontend sends POST requests to /api/v1/auth/token
 * with no body and no Content-Type. When Content-Type: application/json is added
 * by a reverse proxy, Fastify's default JSON parser fails with:
 * FST_ERR_CTP_EMPTY_JSON_BODY: "Body cannot be empty when content-type is set to 'application/json'"
 *
 * This patch must be applied after Fastify is created but before routes are registered.
 */

// This is injected into the app.mjs file
// It replaces the default application/json parser with one that accepts empty bodies

const PATCH_MARKER = '// INFISICAL_EMPTY_BODY_PATCH_APPLIED';

module.exports = function patchFastifyForEmptyJson(server) {
  // Add custom parser for application/json that handles empty bodies
  server.addContentTypeParser('application/json', { parseAs: 'string' }, (req, body, done) => {
    try {
      const strBody = body instanceof Buffer ? body.toString() : body;

      // Handle empty body - return empty object
      if (!strBody || strBody.trim() === '') {
        done(null, {});
        return;
      }

      // Parse JSON normally
      const json = JSON.parse(strBody);
      done(null, json);
    } catch (err) {
      done(err, undefined);
    }
  });

  console.log('[PATCH] Applied empty JSON body fix for Fastify');
  return server;
};
