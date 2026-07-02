USE InventoryDB;
GO

-- Drop CDC tracking on tables if it exists before dropping tables
IF EXISTS (SELECT 1 FROM sys.tables WHERE name = 'adminLoggingArchive' AND is_tracked_by_cdc = 1)
    EXEC sys.sp_cdc_disable_table @source_schema = N'dbo', @source_name = N'adminLoggingArchive', @capture_instance = N'all';
IF EXISTS (SELECT 1 FROM sys.tables WHERE name = 'NeoDest' AND is_tracked_by_cdc = 1)
    EXEC sys.sp_cdc_disable_table @source_schema = N'dbo', @source_name = N'NeoDest', @capture_instance = N'all';
IF EXISTS (SELECT 1 FROM sys.tables WHERE name = 'AdminLogging' AND is_tracked_by_cdc = 1)
    EXEC sys.sp_cdc_disable_table @source_schema = N'dbo', @source_name = N'AdminLogging', @capture_instance = N'all';
IF EXISTS (SELECT 1 FROM sys.tables WHERE name = 'UserSubService' AND is_tracked_by_cdc = 1)
    EXEC sys.sp_cdc_disable_table @source_schema = N'dbo', @source_name = N'UserSubService', @capture_instance = N'all';
IF EXISTS (SELECT 1 FROM sys.tables WHERE name = 'NVUser3' AND is_tracked_by_cdc = 1)
    EXEC sys.sp_cdc_disable_table @source_schema = N'dbo', @source_name = N'NVUser3', @capture_instance = N'all';
IF EXISTS (SELECT 1 FROM sys.tables WHERE name = 'd_oe_user' AND is_tracked_by_cdc = 1)
    EXEC sys.sp_cdc_disable_table @source_schema = N'dbo', @source_name = N'd_oe_user', @capture_instance = N'all';
GO

-- Drop tables if they exist
IF OBJECT_ID('dbo.adminLoggingArchive', 'U') IS NOT NULL DROP TABLE dbo.adminLoggingArchive;
IF OBJECT_ID('dbo.NeoDest', 'U') IS NOT NULL DROP TABLE dbo.NeoDest;
IF OBJECT_ID('dbo.AdminLogging', 'U') IS NOT NULL DROP TABLE dbo.AdminLogging;
IF OBJECT_ID('dbo.UserSubService', 'U') IS NOT NULL DROP TABLE dbo.UserSubService;
IF OBJECT_ID('dbo.NVUser3', 'U') IS NOT NULL DROP TABLE dbo.NVUser3;
IF OBJECT_ID('dbo.d_oe_user', 'U') IS NOT NULL DROP TABLE dbo.d_oe_user;
GO

-- Create Table d_oe_user
CREATE TABLE dbo.d_oe_user (
    [oe_user_sk] BIGINT IDENTITY(1,1) PRIMARY KEY,
    [oe_user_id] VARCHAR(255) NULL,
    [datasource_code] VARCHAR(20) NULL,
    [oe_user_name] VARCHAR(255) NULL,
    [user_given_name] VARCHAR(255) NULL,
    [smp_user_id_txt] VARCHAR(255) NULL,
    [smp_rule_id_num] BIGINT NULL,
    [is_neovest_employee_ind] SMALLINT NULL DEFAULT 0,
    [is_trading_allowed_ind] SMALLINT NULL DEFAULT 1,
    [is_supervisor_ind] SMALLINT NULL DEFAULT 0,
    [is_superuser_ind] SMALLINT NULL DEFAULT 0,
    [is_master_user_ind] SMALLINT NULL DEFAULT 0,
    [is_administrator_ind] SMALLINT NULL DEFAULT 0,
    [is_oe_login_enabled_ind] SMALLINT NULL DEFAULT 1,
    [is_mobile_enabled_ind] SMALLINT NULL DEFAULT -999,
    [is_mobile_username_ind] SMALLINT NULL DEFAULT 0,
    [is_forex_provisioned_ind] SMALLINT NULL DEFAULT -999,
    [first_forex_provisioned_date] DATETIME NULL DEFAULT '1900-01-01 00:00:00',
    [oe_company_sk] BIGINT NULL,
    [oe_account_group_sk] BIGINT NULL,
    [md_user_sk] BIGINT NULL,
    [is_active_ind] SMALLINT NULL,
    [is_deleted_ind] SMALLINT NULL,
    [zzz_col_hash] VARCHAR(255) NULL,
    [zaud_created_by] VARCHAR(255) NULL,
    [zaud_created_ts] DATETIME NULL,
    [zaud_updated_by] VARCHAR(255) NULL,
    [zaud_updated_ts] DATETIME NULL,
    [zaud_unique_id] VARCHAR(255) NULL
);

-- Create Table NVUser3
CREATE TABLE dbo.NVUser3 (
    [NV_User_ID] INT PRIMARY KEY,
    [UserName] VARCHAR(255) NULL,
    [Disabled] INT NULL,
    [LastLogin] DATETIME NULL,
    [UserFlags] BIGINT NULL,
    [Salt] VARCHAR(255) NULL,
    [Verifier] VARCHAR(1000) NULL,
    [GivenName] VARCHAR(255) NULL,
    [Company] VARCHAR(255) NULL,
    [EMail] VARCHAR(255) NULL,
    [Phone] VARCHAR(255) NULL,
    [Address] VARCHAR(1000) NULL,
    [Notes] VARCHAR(MAX) NULL,
    [MaxShares] BIGINT NULL,
    [MaxDollars] BIGINT NULL,
    [IOGFlat] INT NULL,
    [IOGCPS] INT NULL,
    [IOGLog] VARCHAR(1000) NULL,
    [StrategyGroupNumber] INT NULL,
    [UserType] VARCHAR(50) NULL,
    [AccountSubscriptionLimit] INT NULL,
    [Liquidnet] INT NULL,
    [MaxOptShares] BIGINT NULL,
    [MaxOptDollars] BIGINT NULL,
    [ClientVersion] VARCHAR(255) NULL,
    [ClientLocation] VARCHAR(255) NULL,
    [FirstTradeDay] DATETIME NULL,
    [LastTradeDay] DATETIME NULL,
    [Option_MaxNotionalDollars] BIGINT NULL,
    [SpreadOpt_MaxContracts] BIGINT NULL,
    [SpreadOpt_MaxNotionalDollars] BIGINT NULL,
    [FutOption_MaxContracts] BIGINT NULL,
    [FutOption_MaxDollars] BIGINT NULL,
    [FutOption_MaxNotionalDollars] BIGINT NULL,
    [FutSpreadOpt_MaxContracts] BIGINT NULL,
    [FutSpreadOpt_MaxNotionalDollars] BIGINT NULL,
    [IndOption_MaxContracts] BIGINT NULL,
    [IndOption_MaxDollars] BIGINT NULL,
    [IndOption_MaxNotionalDollars] BIGINT NULL,
    [IndSpreadOpt_MaxContracts] BIGINT NULL,
    [IndSpreadOpt_MaxNotionalDollars] BIGINT NULL,
    [FutSpreadOpt_MaxDollars] BIGINT NULL,
    [IndSpreadOpt_MaxDollars] BIGINT NULL,
    [SpreadOpt_MaxDollars] BIGINT NULL,
    [UserName_Secondary] VARCHAR(50) NULL,
    [isMobileEnabled] VARCHAR(50) NULL,
    [MobileUsername] VARCHAR(50) NULL,
    [isExcelEnabled] VARCHAR(50) NULL,
    [ExcelUsername] VARCHAR(50) NULL,
    [isSynthetic] VARCHAR(50) NULL,
    [SyntheticParentID] INT NULL,
    [UserCreatedTime] VARCHAR(50) NULL,
    [UserIsAPICertified] INT NULL,
    [NewAPIOrderMaxCount] INT NULL,
    [NewAPIOrderMaxCountMinutes] INT NULL,
    [APIRejectCount] INT NULL,
    [SMP_RuleID] INT NULL,
    [SMP_UserID] VARCHAR(255) NULL,
    [ArchiveDate] DATETIME NULL,
    [IsSDKEnabled] VARCHAR(50) NULL,
    [SDKUsername] VARCHAR(50) NULL,
    [ApprovedDate] DATETIME NULL,
    [SecurityFlags] INT NULL,
    [SecOutBoundPricePercentThreshold] INT NULL,
    [SecTickIncrementThreshold] INT NULL,
    [SecInBoundPricePercentThreshold] INT NULL,
    [SecStockShareThreshold] INT NULL,
    [SecOptionContThreshold] INT NULL,
    [SecFutureContThreshold] INT NULL,
    [SecFXAmountThreshold] INT NULL,
    [SecHardLimitUSDThreshold] INT NULL
);

-- Create Table UserSubService
CREATE TABLE dbo.UserSubService (
    [id] INT IDENTITY(1,1) PRIMARY KEY,
    [NV_User_ID] INT NULL,
    [Order_Value] INT NULL,
    [Service] VARCHAR(255) NULL,
    [SubService] VARCHAR(255) NULL,
    [EquityShares] BIGINT NULL,
    [EquityDollars] BIGINT NULL,
    [OptionContracts] BIGINT NULL,
    [OptionDollars] BIGINT NULL,
    [Billable] INT NULL
);

-- Create Table AdminLogging
CREATE TABLE dbo.AdminLogging (
    [id] INT IDENTITY(1,1) PRIMARY KEY,
    [NV_User_ID] INT NULL,
    [AdminTimeStamp] DATETIME NULL,
    [AdminString] VARCHAR(255) NULL,
    [AdminIdentity] INT NULL,
    [EntryType] INT NULL,
    [OrderRef] VARCHAR(255) NULL,
    [Reason] VARCHAR(255) NULL,
    [Server] VARCHAR(255) NULL
);

-- Create Table NeoDest
CREATE TABLE dbo.NeoDest (
    [id] INT IDENTITY(1,1) PRIMARY KEY,
    [ServiceID] INT NULL,
    [Dest] VARCHAR(255) NULL,
    [Broker] VARCHAR(255) NULL,
    [ProdType] VARCHAR(50) NULL,
    [Region] VARCHAR(50) NULL,
    [Network] VARCHAR(50) NULL,
    [Middleware] VARCHAR(50) NULL,
    [BrokerID] VARCHAR(255) NULL
);

-- Create Table adminLoggingArchive
CREATE TABLE dbo.adminLoggingArchive (
    [id] INT IDENTITY(1,1) PRIMARY KEY,
    [NV_User_ID] INT NULL,
    [AdminTimeStamp] DATETIME NULL,
    [AdminString] VARCHAR(255) NULL,
    [AdminIdentity] INT NULL,
    [EntryType] INT NULL,
    [OrderRef] VARCHAR(255) NULL,
    [Reason] VARCHAR(255) NULL,
    [Server] VARCHAR(255) NULL
);
GO

-- Enable CDC on DB
IF DB_ID('InventoryDB') IS NOT NULL
BEGIN
    EXEC sys.sp_cdc_enable_db;
END
GO

-- Enable CDC on Tables
EXEC sys.sp_cdc_enable_table @source_schema = N'dbo', @source_name = N'd_oe_user', @role_name = NULL;
EXEC sys.sp_cdc_enable_table @source_schema = N'dbo', @source_name = N'NVUser3', @role_name = NULL;
EXEC sys.sp_cdc_enable_table @source_schema = N'dbo', @source_name = N'UserSubService', @role_name = NULL;
EXEC sys.sp_cdc_enable_table @source_schema = N'dbo', @source_name = N'AdminLogging', @role_name = NULL;
EXEC sys.sp_cdc_enable_table @source_schema = N'dbo', @source_name = N'NeoDest', @role_name = NULL;
EXEC sys.sp_cdc_enable_table @source_schema = N'dbo', @source_name = N'adminLoggingArchive', @role_name = NULL;
GO
