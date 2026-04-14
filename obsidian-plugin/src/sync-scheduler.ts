export interface SyncSchedulerConfig {
    setTimeout: (fn: () => void, delay: number) => number;
    clearTimeout: (id: number) => void;
    random: () => number;
    onSync: (folder: string) => Promise<void>;
    onSchedule: (folder: string, delay: number) => void;
}

const MINUTE = 60 * 1000;
const BASE_INTERVAL_MS = 10 * MINUTE;

export class SyncScheduler {
    private timeoutIds = new Map<string, number>();

    constructor(private config: SyncSchedulerConfig) {}

    start(folders: string[]): void {
        const stagger = BASE_INTERVAL_MS / folders.length;

        folders.forEach((folder, index) => {
            const staggerDelay = index * stagger;
            const flutter = (this.config.random() - 0.5) * stagger * 0.2;
            const delay = staggerDelay + flutter;
            this.scheduleFolder(folder, delay);
        });
    }

    stop(): void {
        for (const id of this.timeoutIds.values()) {
            this.config.clearTimeout(id);
        }
        this.timeoutIds.clear();
    }

    private scheduleFolder(folder: string, delay: number): void {
        this.config.onSchedule(folder, delay);

        const id = this.config.setTimeout(async () => {
            await this.config.onSync(folder);
            this.scheduleNext(folder);
        }, delay);

        this.timeoutIds.set(folder, id);
    }

    private scheduleNext(folder: string): void {
        const flutter = (this.config.random() - 0.5) * BASE_INTERVAL_MS * 0.2;
        const delay = BASE_INTERVAL_MS + flutter;
        this.scheduleFolder(folder, delay);
    }
}
