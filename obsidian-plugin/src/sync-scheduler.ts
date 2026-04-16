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
    private stopped = false;

    constructor(private config: SyncSchedulerConfig) {}

    start(folders: string[]): void {
        const stagger = BASE_INTERVAL_MS / folders.length;

        this.stopped = false;
        folders.forEach((folder, index) => {
            const staggerDelay = index * stagger;
            const flutter = (this.config.random() - 0.5) * stagger * 0.2;
            const delay = staggerDelay + flutter;
            this.scheduleFolder(folder, delay);
        });
    }

    stop(): void {
        this.stopped = true;
        for (const id of this.timeoutIds.values()) {
            this.config.clearTimeout(id);
        }
        this.timeoutIds.clear();
    }

    cancelFolder(folder: string): void {
        const id = this.timeoutIds.get(folder);
        if (id !== undefined) {
            this.config.clearTimeout(id);
            this.timeoutIds.delete(folder);
        }
    }

    addFolder(folder: string): void {
        if (this.timeoutIds.has(folder)) {
            return;
        }
        this.scheduleNext(folder);
    }

    reschedule(folder: string): void {
        this.cancelFolder(folder);
        this.scheduleNext(folder);
    }

    private scheduleFolder(folder: string, delay: number): void {
        if (this.stopped) {
            return;
        }
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
