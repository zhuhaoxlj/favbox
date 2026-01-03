/**
 * 数据库迁移脚本执行器
 * 用于初始化数据库Schema
 */
import fs from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import { pool } from '../src/db.js';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

/**
 * 执行SQL文件
 * @param {string} filePath - SQL文件路径
 */
async function executeSQLFile(filePath) {
  const sql = fs.readFileSync(filePath, 'utf8');

  console.log(`📝 执行迁移: ${filePath}`);

  try {
    await pool.query(sql);
    console.log(`✅ 迁移成功: ${filePath}\n`);
    return true;
  } catch (error) {
    console.error(`❌ 迁移失败: ${filePath}`);
    console.error(`错误: ${error.message}\n`);
    return false;
  }
}

/**
 * 运行所有迁移
 */
async function runMigrations() {
  console.log('🚀 开始数据库迁移...\n');

  const migrationsDir = join(__dirname, '../migrations');
  const files = fs.readdirSync(migrationsDir)
    .filter(f => f.endsWith('.sql'))
    .sort();

  if (files.length === 0) {
    console.log('⚠️  没有找到迁移文件');
    return;
  }

  console.log(`找到 ${files.length} 个迁移文件:\n`);

  let successCount = 0;
  let failCount = 0;

  for (const file of files) {
    const filePath = join(migrationsDir, file);
    const success = await executeSQLFile(filePath);

    if (success) {
      successCount++;
    } else {
      failCount++;
    }
  }

  console.log('📊 迁移统计:');
  console.log(`   成功: ${successCount}`);
  console.log(`   失败: ${failCount}`);
  console.log(`   总计: ${files.length}\n`);

  if (failCount === 0) {
    console.log('✅ 所有迁移执行成功!');
  } else {
    console.log('⚠️  部分迁移执行失败,请检查错误信息');
  }
}

/**
 * 验证数据库连接
 */
async function verifyConnection() {
  try {
    const result = await pool.query('SELECT NOW()');
    console.log(`✅ 数据库连接成功`);
    console.log(`   时间: ${result.rows[0].now}\n`);
    return true;
  } catch (error) {
    console.error(`❌ 数据库连接失败: ${error.message}`);
    console.error(`   请检查.env文件中的数据库配置\n`);
    return false;
  }
}

/**
 * 检查数据库是否已初始化
 */
async function checkInitialized() {
  try {
    const result = await pool.query(`
      SELECT EXISTS (
        SELECT FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name = 'users'
      );
    `);

    return result.rows[0].exists;
  } catch (error) {
    return false;
  }
}

/**
 * 主函数
 */
async function main() {
  console.log('🗄️  FavBox CRDT数据库迁移工具\n');
  console.log('='.repeat(50) + '\n');

  // 验证数据库连接
  const connected = await verifyConnection();
  if (!connected) {
    process.exit(1);
  }

  // 检查是否已初始化
  const isInitialized = await checkInitialized();
  if (isInitialized) {
    console.log('⚠️  数据库已经初始化过了');
    console.log('   如果要重新初始化,请先删除所有表\n');

    const readline = await import('readline');
    const rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout
    });

    rl.question('是否继续执行迁移? (y/N): ', async (answer) => {
      if (answer.toLowerCase() !== 'y') {
        console.log('取消迁移');
        rl.close();
        await pool.end();
        process.exit(0);
      }

      rl.close();
      await runMigrations();
      await pool.end();
      process.exit(0);
    });
  } else {
    await runMigrations();
    await pool.end();
    process.exit(0);
  }
}

// 运行迁移
main().catch((error) => {
  console.error('❌ 迁移过程出错:', error);
  process.exit(1);
});
