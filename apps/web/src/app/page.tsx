import { CheckCircle2, AlertTriangle, Info, MapPin, User, Package, ChevronRight } from "lucide-react";
import clsx from "clsx";

export default function Home() {
  return (
    <div className="flex h-screen bg-[#fcfcfc] text-gray-900 overflow-hidden font-sans">
      {/* Left Column: Scene Navigator */}
      <div className="w-64 border-r border-gray-200 bg-white flex flex-col">
        <div className="p-4 border-b border-gray-200">
          <h1 className="text-sm font-semibold tracking-wide text-gray-900">STORYTRACE</h1>
          <p className="text-xs text-gray-500 mt-1">demo_script.pdf</p>
        </div>
        <div className="flex-1 overflow-y-auto p-2">
          {/* Mock Scene List */}
          {[1, 2, 3, 4, 5, 6].map((scene) => (
            <div key={scene} className={clsx("px-3 py-2 text-sm rounded-md mb-1 cursor-pointer flex justify-between items-center group transition-colors", scene === 3 ? "bg-blue-50 text-blue-700 font-medium" : "text-gray-600 hover:bg-gray-100")}>
              <span>Scene {scene}</span>
              {scene === 3 && <AlertTriangle className="w-4 h-4 text-amber-500" />}
            </div>
          ))}
        </div>
      </div>

      {/* Center Column: Screenplay Text */}
      <div className="flex-1 flex flex-col bg-[#f5f5f5] shadow-inner">
        <div className="p-4 border-b border-gray-200 bg-white flex justify-between items-center">
          <div className="flex gap-4 text-xs font-medium text-gray-500 uppercase tracking-wider">
            <span>Pg. 16</span>
            <span className="text-gray-300">|</span>
            <span>Scene 3</span>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto p-12 flex justify-center">
          <div className="w-full max-w-2xl bg-white shadow-sm border border-gray-200 p-12 min-h-full font-mono text-[13px] leading-relaxed">
            <p className="mb-6 font-bold">INT. WAREHOUSE - NIGHT</p>
            <p className="mb-6">JOHN (40s), battered but determined, stands in the middle of a dusty warehouse. He pulls out a SILVER PISTOL.</p>
            <div className="w-1/2 mx-auto mb-6">
              <p className="text-center mb-2">JOHN</p>
              <p>It ends tonight.</p>
            </div>
            <p className="mb-6 font-bold">EXT. ALLEYWAY - LATER</p>
            <p className="mb-6 bg-amber-100 px-1 -mx-1 rounded">John raises the silver pistol. Where did he get it?</p>
          </div>
        </div>
      </div>

      {/* Right Column: Findings/Autopsy */}
      <div className="w-96 border-l border-gray-200 bg-white flex flex-col">
        <div className="p-4 border-b border-gray-200 flex justify-between items-center">
          <h2 className="text-sm font-semibold">Continuity Findings</h2>
          <span className="bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full text-xs font-medium">3 Issues</span>
        </div>
        
        <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-4">
          
          {/* Autopsy Card */}
          <div className="border border-red-200 rounded-lg overflow-hidden bg-white shadow-sm">
            <div className="bg-red-50 px-3 py-2 border-b border-red-200 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-red-600" />
              <span className="text-sm font-semibold text-red-900">VERIFIED CONFLICT</span>
            </div>
            <div className="p-4">
              <div className="flex items-center gap-2 text-sm font-medium mb-1">
                <Package className="w-4 h-4 text-gray-500" />
                <span>Silver Pistol</span>
              </div>
              <p className="text-xs text-gray-500 mb-4">Scenes 16 → 22</p>

              <div className="mb-4">
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Prior State</p>
                <div className="bg-gray-50 p-2 rounded text-xs border border-gray-200">
                  <p className="text-gray-500 italic mb-1">Scene 16 · p48</p>
                  <p>"The gun clatters to the floor."</p>
                  <span className="inline-block mt-1 px-1.5 py-0.5 bg-gray-200 text-gray-700 rounded-sm text-[10px] font-bold">LOST</span>
                </div>
              </div>

              <div className="mb-4">
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1">Observed State</p>
                <div className="bg-amber-50 p-2 rounded text-xs border border-amber-200">
                  <p className="text-gray-500 italic mb-1">Scene 22 · p61</p>
                  <p>"John raises the gun."</p>
                  <span className="inline-block mt-1 px-1.5 py-0.5 bg-amber-200 text-amber-800 rounded-sm text-[10px] font-bold">HELD</span>
                </div>
              </div>
              
              <div className="pt-4 border-t border-gray-100">
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Investigation Trace</p>
                <ul className="text-xs text-gray-600 space-y-1 mb-4">
                  <li className="flex items-center gap-1"><CheckCircle2 className="w-3 h-3 text-green-500"/> Retrieved entity history</li>
                  <li className="flex items-center gap-1"><CheckCircle2 className="w-3 h-3 text-green-500"/> Examined Scenes 17–21</li>
                  <li className="flex items-center gap-1"><CheckCircle2 className="w-3 h-3 text-green-500"/> Checked recovery events</li>
                  <li className="flex items-center gap-1"><span className="text-red-500 w-3 h-3 text-center leading-3 font-bold">×</span> No recovery found</li>
                </ul>
                <div className="bg-gray-50 p-3 rounded-md text-sm text-gray-800 border border-gray-200">
                  No screenplay evidence explains how John regained the gun.
                </div>
              </div>

              <div className="mt-4 flex gap-2">
                <button className="flex-1 bg-white border border-gray-300 text-gray-700 py-1.5 rounded text-xs font-medium hover:bg-gray-50 transition-colors">Mark Intentional</button>
              </div>
            </div>
          </div>

          {/* Resolved Card */}
          <div className="border border-gray-200 rounded-lg overflow-hidden bg-white shadow-sm opacity-75 hover:opacity-100 transition-opacity">
            <div className="bg-gray-50 px-3 py-2 border-b border-gray-200 flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-gray-500" />
              <span className="text-sm font-medium text-gray-700">RESOLVED</span>
            </div>
            <div className="p-4 pb-3">
              <div className="flex items-center gap-2 text-sm font-medium mb-1">
                <User className="w-4 h-4 text-gray-500" />
                <span>John's Bandage</span>
              </div>
              <p className="text-xs text-gray-500 mb-2">Scenes 31 → 34</p>
              <p className="text-xs text-gray-600">Scene 33 establishes: <br/><span className="italic">"John removes the bandages."</span><br/><br/>This explains the state transition.</p>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
