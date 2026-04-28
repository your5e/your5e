export interface FileSystem {
    read(path: string): Promise<Buffer>;
    write(path: string, content: Buffer): Promise<void>;
    rename(from: string, to: string): Promise<void>;
    delete(path: string): Promise<void>;
    list(dir: string): Promise<string[]>;
    hash(path: string): Promise<string>;
    exists(path: string): Promise<boolean>;
    isFile(path: string): Promise<boolean>;
    isDirectory(path: string): Promise<boolean>;
    mkdir(path: string): Promise<void>;
    findCaseInsensitive(dir: string, name: string): Promise<string | null>;
}

export interface SyncStateEntry {
    uuid: string;
    serverFilename: string;
    localFilename: string;
    serverHash: string;
    localHash: string;
    localDeleted?: boolean;
}

export interface SyncConfig {
    baseUrl: string;
    token: string;
    notebook: string;
    outputDir: string;
    fileSystem: FileSystem;
    initialState?: Map<string, SyncStateEntry>;
    pullOnly?: boolean;
    timeoutMs?: number;
    lastUpdate?: string;
    lastFullSync?: string;
    afterFetchHook?: () => Promise<void>;
    onOutput?: (line: string) => void;
    abortSignal?: AbortSignal;
    hostname?: string;
}

export interface SyncResult {
    output: string[];
    state: Map<string, SyncStateEntry>;
    lastUpdate?: string;
    lastFullSync?: string;
    /** Results from incremental sync query (undefined for full sync) */
    incrementalResults?: number;
}
