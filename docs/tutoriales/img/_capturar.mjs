/**
 * Captura los pantallazos de la guia rapida de usuario (docs/tutoriales/guia_rapida_usuario.md).
 *
 * Todas las capturas salen de la organizacion de demostracion "Colegio Demo",
 * cuyos datos son sinteticos ("Estudiante Demo 01"...): no aparece ningun dato
 * personal real en las imagenes.
 *
 * ── Requisitos ────────────────────────────────────────────────────────────
 *   1. Stack de desarrollo levantado:
 *        docker compose -f docker-compose.dev.yml up -d
 *      (frontend en :5173, backend en :8001)
 *
 *   2. Organizacion de demo poblada. Si no existe:
 *        docker compose -f docker-compose.dev.yml exec -T backend \
 *          python scripts/crear_org_demo.py --reset
 *
 *   3. Playwright instalado FUERA del repo (para no tocar package.json):
 *        mkdir -p ~/tmp_screenshots && cd ~/tmp_screenshots
 *        npm init -y && npm i playwright && npx playwright install chromium
 *
 * ── Uso ───────────────────────────────────────────────────────────────────
 *   Desde la raiz del repo:
 *     node docs/tutoriales/img/_capturar.mjs
 *
 *   Variables opcionales: APP_URL, PLAYWRIGHT_DIR.
 *
 * Genera los 9 PNG de la guia en esta misma carpeta. Los 8 primeros son
 * capturas del navegador; informe_pdf.png sale de convertir la pagina 1 del
 * PDF descargado (lo hace _pdf_a_png.py dentro del contenedor backend, que es
 * donde esta PyMuPDF).
 *
 * SEGURIDAD: el paso del modal "Importar Datos" solo abre la ventana y la
 * cierra con Cancelar. NUNCA se completa una importacion real.
 */
import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';
import { mkdirSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

// Playwright vive FUERA del repo para no modificar package.json.
const require = createRequire(import.meta.url);
const PLAYWRIGHT_DIR =
  process.env.PLAYWRIGHT_DIR || process.env.HOME + '/tmp_screenshots/node_modules/playwright';
const { chromium } = require(PLAYWRIGHT_DIR);

const OUT = dirname(fileURLToPath(import.meta.url));
const REPO = resolve(OUT, '..', '..', '..');
const APP = process.env.APP_URL || 'http://localhost:5173';
const USER = 'demo@rgenerator.local';
const PASS = 'demo1234';

mkdirSync(OUT, { recursive: true });

const shot = async (page, name) => {
  await page.waitForTimeout(700);
  await page.screenshot({ path: join(OUT, name) });
  console.log('  OK', name);
};

/** Clic en una zona neutra de la cabecera (cierra dropdowns sin navegar). */
const clickNeutral = (page) => page.mouse.click(1000, 60);

const run = async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({
    viewport: { width: 1280, height: 800 },
    deviceScaleFactor: 2,
    colorScheme: 'light',
    locale: 'es-CL',
    acceptDownloads: true,
  });
  // Fuerza tema claro antes de que arranque React
  await ctx.addInitScript(() => localStorage.setItem('theme', 'light'));
  const page = await ctx.newPage();

  // -- 1. Login ------------------------------------------------------------
  console.log('1. login');
  await page.goto(`${APP}/login`, { waitUntil: 'networkidle' });
  await page.fill('input[type="email"]', USER);
  await page.fill('input[type="password"]', PASS);
  await shot(page, 'login.png');

  await page.click('button[type="submit"]');
  await page.waitForURL((u) => !u.pathname.includes('login'), { timeout: 20000 });
  await page.waitForTimeout(1500);

  // -- 2. Centro de Ejecucion ----------------------------------------------
  // OJO: usamos /execution (menu "Ejecución"), que es la pantalla pensada para
  // el usuario final. /pipelines ("Procesos") es la vista de administracion,
  // con editar/borrar, y no corresponde a esta guia.
  console.log('2. pipelines');
  await page.goto(`${APP}/execution`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1500);
  const tarjetaSimce = page
    .locator('div')
    .filter({ hasText: 'Carga SIMCE Demo' })
    .locator('button', { hasText: 'Ejecutar Proceso' })
    .last();
  await tarjetaSimce.hover(); // resalta la tarjeta y su boton
  await shot(page, 'pipelines.png');

  // -- 3. Modal de ejecucion pidiendo archivos -----------------------------
  console.log('3. carga_archivos');
  await tarjetaSimce.click();
  await page.waitForTimeout(1200);
  for (let i = 0; i < 4; i++) {
    if (await page.locator('text=/Resultados por Estudiante/i').first().count()) break;
    const next = page.locator('button', { hasText: /Siguiente|Continuar/ }).first();
    if (!(await next.count())) break;
    await next.click();
    await page.waitForTimeout(2500);
  }
  await page.waitForTimeout(1200);
  await shot(page, 'carga_archivos.png');
  const cerrar = page.locator('button', { hasText: /^Cerrar$/ }).first();
  if (await cerrar.count()) await cerrar.click();
  await page.waitForTimeout(800);

  // -- 4. Valores (con el panel de filtros desplegado) ---------------------
  console.log('4. values');
  await page.goto(`${APP}/values`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1500);
  await page.locator('text=Resultados SIMCE Demo por Estudiante').first().click();
  await page.waitForTimeout(2500);

  // -- 4b. Modal "Importar Datos" (camino 2.2 de la guia) ------------------
  // OJO: solo se abre la ventana para la captura y se cierra con Cancelar.
  // No se selecciona ningun archivo ni se aprieta "Importar".
  console.log('4b. importar_valores');
  await page.getByRole('button', { name: /Importar/ }).first().click();
  await page.waitForTimeout(1500);
  await shot(page, 'importar_valores.png');
  await page.getByRole('button', { name: /^Cancelar$/ }).first().click();
  await page.waitForTimeout(800);

  // Ojo: el boton trae un icono delante, asi que su texto es " Filtros".
  // getByRole normaliza el nombre accesible; un regex anclado (/^Filtros/)
  // sobre hasText NO lo encuentra.
  await page.getByRole('button', { name: /Filtros/ }).first().click();
  await page.waitForTimeout(1800);
  await shot(page, 'values.png');

  // -- 5. Dashboard --------------------------------------------------------
  console.log('5. dashboard');
  await page.goto(`${APP}/results`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1200);
  await page.selectOption('select', { label: 'SIMCE Demo Lenguaje' });
  await page.waitForTimeout(6000);
  // El dashboard completo mide ~1650px. Con este scroll la ventana de 800px
  // encuadra pestañas + KPIs + tabla resumen + la primera fila de graficos.
  await page.evaluate(() => window.scrollTo(0, 345));
  await page.waitForTimeout(1200);
  await shot(page, 'dashboard.png');

  // -- 6. Dashboard con un filtro aplicado (chips visibles) ----------------
  console.log('6. dashboard_filtros');
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(800);
  await page.locator('button').filter({ hasText: /^Curso$/ }).first().click();
  await page.waitForTimeout(900);
  await page.locator('label', { hasText: '1° Medio A' }).first().click();
  await page.waitForTimeout(1500);
  await clickNeutral(page);
  await page.waitForTimeout(4500);
  await shot(page, 'dashboard_filtros.png');

  // -- 7. Modal "Generar informe" ------------------------------------------
  console.log('7. generar_informe');
  await page.locator('button', { hasText: 'Generar informe' }).first().click();
  await page.waitForTimeout(3500);
  await shot(page, 'generar_informe.png');

  // -- 8. PDF: descarga desde la UI ----------------------------------------
  // El PDF crudo se deja en data/tmp/ (montado en el contenedor backend).
  // La conversion a PNG la hace _pdf_a_png.py — ver README.
  console.log('8. descargando PDF (Informe ultima prueba)');
  try {
    const [download] = await Promise.all([
      page.waitForEvent('download', { timeout: 180000 }),
      page.locator('button', { hasText: 'Informe última prueba' }).first().click(),
    ]);
    const destino = join(REPO, 'data', 'tmp', '_informe_guia.pdf');
    await download.saveAs(destino);
    console.log('  OK pdf ->', destino);

    // La pagina 1 se convierte a PNG con PyMuPDF, que vive en el contenedor.
    // --user con el uid/gid del host evita que el PNG quede como root en el repo.
    const uid = typeof process.getuid === 'function' ? process.getuid() : 1000;
    const gid = typeof process.getgid === 'function' ? process.getgid() : 1000;
    execFileSync(
      'docker',
      [
        'compose', '-f', 'docker-compose.dev.yml', 'exec', '-T',
        '--user', `${uid}:${gid}`, 'backend',
        'python', '/app/docs/tutoriales/img/_pdf_a_png.py',
      ],
      { cwd: REPO, stdio: 'inherit' }
    );
  } catch (e) {
    console.log('  ! informe_pdf.png fallo:', e.message);
  }

  await browser.close();
  console.log('Listo. Capturas en', OUT);
};

run().catch((e) => {
  console.error(e);
  process.exit(1);
});
