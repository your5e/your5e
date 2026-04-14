import { describe, expect, it } from "vitest";
import { SyncScheduler } from "../src/sync-scheduler.js";

describe("sync scheduler", () => {
    it("staggers initial syncs across the interval", () => {
        const scheduled: Array<{ folder: string; delay: number }> = [];
        const mockSetTimeout = (fn: () => void, delay: number) => {
            return scheduled.length + 1;
        };
        const mockClearTimeout = (_id: number) => {};

        // 0.5 produces zero flutter, isolating the stagger measurement
        const mockRandom = () => 0.5;
        const scheduler = new SyncScheduler({
            setTimeout: mockSetTimeout,
            clearTimeout: mockClearTimeout,
            random: mockRandom,
            onSync: async (folder) => {},
            onSchedule: (folder, delay) => {
                scheduled.push({ folder, delay });
            },
        });

        scheduler.start(["notes", "journal", "archive"]);

        expect(scheduled).toHaveLength(3);

        const delays = scheduled.map((s) => s.delay);
        expect(delays[0]).toBeLessThan(delays[1]);
        expect(delays[1]).toBeLessThan(delays[2]);

        const gap1 = delays[1] - delays[0];
        const gap2 = delays[2] - delays[1];
        expect(gap1).toBeGreaterThan(180000);
        expect(gap1).toBeLessThan(220000);
        expect(gap2).toBeGreaterThan(180000);
        expect(gap2).toBeLessThan(220000);
    });

    it("applies random flutter to initial scheduling", () => {
        const scheduled: Array<{ folder: string; delay: number }> = [];
        const mockSetTimeout = (fn: () => void, delay: number) => {
            return scheduled.length + 1;
        };
        const mockClearTimeout = (_id: number) => {};

        let randomIndex = 0;
        const randomValues = [0.0, 0.5, 1.0];
        const mockRandom = () => randomValues[randomIndex++];
        const scheduler = new SyncScheduler({
            setTimeout: mockSetTimeout,
            clearTimeout: mockClearTimeout,
            random: mockRandom,
            onSync: async (folder) => {},
            onSchedule: (folder, delay) => {
                scheduled.push({ folder, delay });
            },
        });

        scheduler.start(["notes", "journal", "archive"]);
        expect(scheduled[0].delay).toBeLessThan(200000);
        expect(scheduled[1].delay).toBeCloseTo(200000, -4);
        expect(scheduled[2].delay).toBeGreaterThan(400000);
    });

    it("schedules next sync with fresh flutter after completion", async () => {
        const scheduled: Array<{ folder: string; delay: number }> = [];
        const callbacks = new Map<number, () => void>();
        let nextId = 1;

        const mockSetTimeout = (fn: () => void, delay: number) => {
            const id = nextId++;
            callbacks.set(id, fn);
            return id;
        };
        const mockClearTimeout = (_id: number) => {};

        let randomIndex = 0;
        const randomValues = [0.5, 0.0, 1.0];
        const mockRandom = () => randomValues[randomIndex++];

        let syncCount = 0;
        const scheduler = new SyncScheduler({
            setTimeout: mockSetTimeout,
            clearTimeout: mockClearTimeout,
            random: mockRandom,
            onSync: async (folder) => {
                syncCount++;
            },
            onSchedule: (folder, delay) => {
                scheduled.push({ folder, delay });
            },
        });

        scheduler.start(["notes"]);
        expect(scheduled).toHaveLength(1);

        const firstCallback = callbacks.get(1);
        expect(firstCallback).toBeDefined();
        await firstCallback?.();

        expect(syncCount).toBe(1);
        expect(scheduled).toHaveLength(2);
        expect(scheduled[1].delay).toBeLessThan(600000);
        expect(scheduled[1].delay).toBeGreaterThan(500000);
    });

    it("reschedules with 10 minute base interval ±1 minute flutter", async () => {
        const scheduled: Array<{ folder: string; delay: number }> = [];
        const callbacks = new Map<number, () => void>();
        let nextId = 1;

        const mockSetTimeout = (fn: () => void, delay: number) => {
            const id = nextId++;
            callbacks.set(id, fn);
            return id;
        };
        const mockClearTimeout = (_id: number) => {};

        let randomIndex = 0;
        const randomValues = [0.5, 0.5, 0.0, 1.0];
        const mockRandom = () => randomValues[randomIndex++];

        const scheduler = new SyncScheduler({
            setTimeout: mockSetTimeout,
            clearTimeout: mockClearTimeout,
            random: mockRandom,
            onSync: async (folder) => {},
            onSchedule: (folder, delay) => {
                scheduled.push({ folder, delay });
            },
        });

        scheduler.start(["first", "second"]);
        await callbacks.get(1)?.();
        await callbacks.get(2)?.();

        expect(scheduled[2].delay).toBeCloseTo(540000, -3);
        expect(scheduled[3].delay).toBeCloseTo(660000, -3);
    });

    it("clears pending timeouts when stopped", () => {
        const clearedIds: number[] = [];
        let nextId = 1;

        const mockSetTimeout = (fn: () => void, delay: number) => {
            return nextId++;
        };
        const mockClearTimeout = (id: number) => {
            clearedIds.push(id);
        };
        const mockRandom = () => 0.5;

        const scheduler = new SyncScheduler({
            setTimeout: mockSetTimeout,
            clearTimeout: mockClearTimeout,
            random: mockRandom,
            onSync: async (folder) => {},
            onSchedule: (folder, delay) => {},
        });

        scheduler.start(["notes", "journal"]);
        scheduler.stop();

        expect(clearedIds).toContain(1);
        expect(clearedIds).toContain(2);
    });

    it("schedules folders independently", async () => {
        const syncedFolders: string[] = [];
        const callbacks = new Map<number, () => void>();
        let nextId = 1;

        const mockSetTimeout = (fn: () => void, delay: number) => {
            const id = nextId++;
            callbacks.set(id, fn);
            return id;
        };
        const mockClearTimeout = (_id: number) => {};
        const mockRandom = () => 0.5;

        const scheduler = new SyncScheduler({
            setTimeout: mockSetTimeout,
            clearTimeout: mockClearTimeout,
            random: mockRandom,
            onSync: async (folder) => {
                syncedFolders.push(folder);
            },
            onSchedule: (folder, delay) => {},
        });

        scheduler.start(["notes", "journal"]);

        await callbacks.get(1)?.();
        expect(syncedFolders).toEqual(["notes"]);

        await callbacks.get(2)?.();
        expect(syncedFolders).toEqual(["notes", "journal"]);
    });
});
