var __defProp = Object.defineProperty;
var __name = (target, value) => __defProp(target, "name", { value, configurable: true });

// node_modules/tsup/assets/esm_shims.js
import path from "path";
import { fileURLToPath } from "url";
var getFilename = /* @__PURE__ */ __name(() => fileURLToPath(import.meta.url), "getFilename");
var getDirname = /* @__PURE__ */ __name(() => path.dirname(getFilename()), "getDirname");
var __dirname = /* @__PURE__ */ getDirname();

// src/server/app.ts
import path2 from "path";
import cookie from "@fastify/cookie";
import cors from "@fastify/cors";
import fastifyEtag from "@fastify/etag";
import fastifyFormBody from "@fastify/formbody";
import helmet from "@fastify/helmet";
import ratelimiter from "@fastify/rate-limit";
import { fastifyRequestContext } from "@fastify/request-context";
import fastify from "fastify";
import { getConfig, IS_PACKAGED } from "../lib/config/env.mjs";
import { alphaNumericNanoId } from "../lib/nanoid/index.mjs";
import { globalRateLimiterCfg } from "./config/rateLimiter.mjs";
import { addErrorsToResponseSchemas } from "./plugins/add-errors-to-response-schemas.mjs";
import { apiMetrics } from "./plugins/api-metrics.mjs";
import { fastifyErrHandler } from "./plugins/error-handler.mjs";
import { serializerCompiler, validatorCompiler } from "./plugins/fastify-zod.mjs";
import { fastifyIp } from "./plugins/ip.mjs";
import { maintenanceMode } from "./plugins/maintenanceMode.mjs";
import { registerServeUI } from "./plugins/serve-ui.mjs";
import { fastifySwagger } from "./plugins/swagger.mjs";
import { registerRoutes } from "./routes/index.mjs";
var main = /* @__PURE__ */ __name(async ({
  db,
  auditLogDb,
  smtp,
  logger,
  queue,
  keyStore,
  redis,
  envConfig,
  superAdminDAL,
  hsmService,
  kmsRootConfigDAL
}) => {
  const appCfg = getConfig();
  const server = fastify({
    logger: appCfg.NODE_ENV === "test" ? false : logger,
    genReqId: /* @__PURE__ */ __name(() => `req-${alphaNumericNanoId(14)}`, "genReqId"),
    trustProxy: true,
    connectionTimeout: appCfg.isHsmConfigured ? 9e4 : 3e4,
    ignoreTrailingSlash: true,
    pluginTimeout: 4e4
  }).withTypeProvider();
  server.setValidatorCompiler(validatorCompiler);
  server.setSerializerCompiler(serializerCompiler);
  server.decorate("redis", redis);

  // PATCH: Custom application/json parser that accepts empty bodies
  // Fixes FST_ERR_CTP_EMPTY_JSON_BODY error when frontend sends POST with no body
  // This overrides Fastify's default JSON parser
  server.addContentTypeParser("application/json", { parseAs: "string" }, (req, body, done) => {
    try {
      const strBody = body instanceof Buffer ? body.toString() : body;
      // Handle empty body - return empty object instead of throwing error
      if (!strBody || strBody.trim() === "") {
        done(null, {});
        return;
      }
      const json = JSON.parse(strBody);
      done(null, json);
    } catch (err) {
      done(err, void 0);
    }
  });
  console.log("[PATCH] Applied empty JSON body fix for Fastify");
  // END PATCH

  server.addContentTypeParser("application/scim+json", { parseAs: "string" }, (_, body, done) => {
    try {
      const strBody = body instanceof Buffer ? body.toString() : body;
      if (!strBody) {
        done(null, void 0);
        return;
      }
      const json = JSON.parse(strBody);
      done(null, json);
    } catch (err) {
      const error = err;
      done(error, void 0);
    }
  });
  try {
    await server.register(cookie, {
      secret: appCfg.COOKIE_SECRET_SIGN_KEY
    });
    await server.register(fastifyEtag);
    await server.register(cors, {
      credentials: true,
      ...appCfg.CORS_ALLOWED_ORIGINS?.length ? {
        origin: [...appCfg.CORS_ALLOWED_ORIGINS, ...appCfg.SITE_URL ? [appCfg.SITE_URL] : []]
      } : {
        origin: appCfg.SITE_URL || true
      },
      ...appCfg.CORS_ALLOWED_HEADERS?.length && {
        allowedHeaders: appCfg.CORS_ALLOWED_HEADERS
      }
    });
    await server.register(addErrorsToResponseSchemas);
    await server.register(fastifyIp);
    if (appCfg.OTEL_TELEMETRY_COLLECTION_ENABLED) {
      await server.register(apiMetrics);
    }
    await server.register(fastifySwagger);
    await server.register(fastifyFormBody);
    await server.register(fastifyErrHandler);
    if (appCfg.isProductionMode && appCfg.isCloud) {
      await server.register(ratelimiter, globalRateLimiterCfg());
    }
    await server.register(helmet, { contentSecurityPolicy: false });
    await server.register(maintenanceMode);
    await server.register(fastifyRequestContext, {
      defaultStoreValues: /* @__PURE__ */ __name((req) => ({
        reqId: req.id,
        log: req.log.child({ reqId: req.id }),
        ip: req.realIp,
        userAgent: req.headers["user-agent"]
      }), "defaultStoreValues")
    });
    await server.register(registerRoutes, {
      smtp,
      queue,
      db,
      auditLogDb,
      keyStore,
      hsmService,
      envConfig,
      superAdminDAL,
      kmsRootConfigDAL
    });
    await server.register(registerServeUI, {
      standaloneMode: appCfg.STANDALONE_MODE || IS_PACKAGED,
      dir: path2.join(__dirname, IS_PACKAGED ? "../../../" : "../../")
    });
    await server.ready();
    server.swagger();
    return server;
  } catch (err) {
    server.log.error(err);
    await queue.shutdown();
    process.exit(1);
  }
}, "main");
export {
  main
};
//# sourceMappingURL=app.mjs.map
