"""ROSA Builder: GUI by default, offline CLI for reproducibility tests."""
from pathlib import Path
import argparse,json,os,queue,sys,threading,tempfile,zipfile
import core
import guided_workflow as workflow

def resource(name):return Path(getattr(sys,'_MEIPASS',Path(__file__).parent))/name
def release():return json.loads(resource('release.json').read_text())
def default_data():return Path(sys.executable if getattr(sys,'frozen',False) else __file__).parent/'ROSA-Builder.data'

def cli():
    p=argparse.ArgumentParser(description='Offline ROSA Builder Preview 0.1')
    p.add_argument('--cli',choices=['check','build','diagnose','setup-mesa','diagnose-sdk'],required=True)
    p.add_argument('--rom',type=Path)
    p.add_argument('--output',type=Path)
    p.add_argument('--devkitpro',type=Path,default=None)
    p.add_argument('--mesa',type=Path,default=None)
    p.add_argument('--mesa-mode',choices=['auto','existing','import'],default='auto')
    p.add_argument('--mesa-archive',type=Path)
    p.add_argument('--data',type=Path,default=default_data())
    p.add_argument('--font',type=Path)
    p.add_argument('--jobs',type=int,default=2)
    p.add_argument('--allow-code-equivalent',action='store_true',
                   help='Experimental: same game code and exheader, different resources; unvalidated on Switch.')
    p.add_argument('--managed-sdk',action='store_true',
                   help='Download verified devkitPro packages into the new build folder. Mesa SDK is prepared automatically by default.')
    p.add_argument('--report',type=Path,required=True,help='New local report file, never uploaded')
    a=p.parse_args()
    if a.report.exists():raise core.BuildError('Report already exists; preserved.')
    events=[]
    def emit(**event):
        events.append(event)
        # Real stage counters, not simulated time-based percentages.
        with a.report.open('a',encoding='utf-8') as f:f.write(json.dumps(event)+'\n')
    try:
        if a.cli in ('build','check'):
            a.devkitpro,a.managed_sdk=workflow.choose_dependencies(a.data,release()['data_sha256'],a.devkitpro,a.managed_sdk,emit)
        if a.cli=='setup-mesa':
            import mesa_sdk
            with tempfile.TemporaryDirectory(prefix='rosa-mesa-setup-') as temp:
                payload=Path(temp)/'payload'
                core.unpack_payload(a.data,payload,release()['data_sha256'])
                mesa_sdk.setup(payload,a.mesa_mode,existing=a.mesa,archive=a.mesa_archive,emit=emit)
            emit(stage='complete',message='Mesa SDK verified. No game input was read.')
        elif a.cli=='diagnose-sdk':
            details=workflow.sdk_report(a.data,release()['data_sha256'],a.mesa_mode,a.mesa,a.mesa_archive)
            emit(stage='checked',message='Mesa SDK file hashes and AArch64 objects verified.',sdk=details,package=workflow.package_report(a.data))
        elif not a.rom:raise core.BuildError('Select your personal dump.')
        elif a.cli=='diagnose':
            details=workflow.rom_report(a.rom,a.allow_code_equivalent)
            emit(stage='diagnosed',message=details['message'],diagnostic=details,package=workflow.package_report(a.data))
        elif a.cli=='check':
            result=core.validate_rom(a.rom,allow_code_equivalent=a.allow_code_equivalent)
            if core.sha(a.data)!=release()['data_sha256']:raise core.BuildError('Payload integrity mismatch.')
            with tempfile.TemporaryDirectory(prefix='rosa-sdk-check-') as temp:
                payload=Path(temp)/'payload'
                core.unpack_payload(a.data,payload,release()['data_sha256'])
                import mesa_sdk,sdk
                mesa=mesa_sdk.setup(payload,a.mesa_mode,existing=a.mesa,archive=a.mesa_archive,emit=emit)
                if a.managed_sdk:
                    plan=sdk._load_plan(payload)
                    sdk.verify_mesa_files(payload,mesa)
                    emit(stage='checked',message='Dump, official SDK plan and Mesa verified. devkitPro downloads begin only during build.',result=result,packages=len(plan['packages']))
                else:
                    core.check_tools(a.devkitpro,mesa);sdk.verify_sdk_files(payload,a.devkitpro,mesa)
                    emit(stage='checked',message='Dump and detected installed SDK verified. This is not a full build.',result=result)
        else:
            if not a.output:raise core.BuildError('A new output directory is required.')
            result=core.build(a.rom,a.output,a.devkitpro,a.mesa,a.data,release()['data_sha256'],emit,a.jobs,a.font,managed_sdk=a.managed_sdk,allow_code_equivalent=a.allow_code_equivalent,mesa_mode=a.mesa_mode,mesa_archive=a.mesa_archive)
    except Exception as error:
        message=str(error) if isinstance(error,core.BuildError) else 'Unexpected failure. Preserve this workspace for private diagnosis.'
        emit(stage='error',message=message,**({'sdk':error.diagnostic} if hasattr(error,'diagnostic') else {}));return 1
    return 0

def gui():
    import tkinter as tk
    from tkinter import ttk,filedialog,messagebox
    win=tk.Tk();win.title('ROSA Builder R9 - Guided Preview');win.geometry('820x710');win.minsize(740,650)
    if '--ui-smoke-report' in sys.argv:win.withdraw()
    style=ttk.Style(win);style.theme_use('clam')
    style.configure('.',font=('Segoe UI',10));style.configure('TButton',padding=7)
    frame=ttk.Frame(win,padding=24);frame.pack(fill='both',expand=True)
    ttk.Label(frame,text='ROSA Builder',font=('Segoe UI',26,'bold')).pack(anchor='w')
    ttk.Label(frame,text='R9 Guided Preview | B20 runtime | Your game stays on your PC').pack(anchor='w',pady=(0,12))
    fields={};controls=[];events=[];snapshot={};active=False;last=None
    messages=queue.Queue(maxsize=48)
    def field(parent,key,label,directory=False,default='',types=None):
        row=ttk.Frame(parent);row.pack(fill='x',pady=5)
        ttk.Label(row,text=label,width=19).pack(side='left')
        var=tk.StringVar(value=default);fields[key]=var
        entry=ttk.Entry(row,textvariable=var);entry.pack(side='left',fill='x',expand=True);controls.append(entry)
        def choose():
            value=filedialog.askdirectory(parent=win) if directory else filedialog.askopenfilename(parent=win,filetypes=types or [('All files','*')])
            if value:var.set(value)
        button=ttk.Button(row,text='Browse',command=choose);button.pack(side='left',padx=(8,0));controls.append(button)
    field(frame,'rom','1. Your game dump',types=[('NCSD cartridge dump','*.3ds *.cci'),('All files','*')])
    field(frame,'output','2. Output parent',True,str(Path.home()/'ROSA Builds'))
    ttk.Label(frame,text='3. Dependencies: automatic. Compatible installed devkitPro is reused; otherwise verified official packages are downloaded into the new build. Mesa is prepared from the matching DATA file.',wraplength=740).pack(anchor='w',pady=10)
    steps={}
    for name,label in [('validate','Game compatibility'),('sdk','Dependencies'),('compile','Native build'),('complete','SD output')]:
        value=tk.StringVar(value=label+' - waiting');steps[name]=value;ttk.Label(frame,textvariable=value).pack(anchor='w',pady=2)
    state=tk.StringVar(value='Choose your own dump and an output folder. No SDK paths are required.')
    ttk.Label(frame,textvariable=state,wraplength=740).pack(anchor='w',pady=(12,4))
    bar=ttk.Progressbar(frame,mode='determinate');bar.pack(fill='x',pady=5)
    buttons=ttk.Frame(frame);buttons.pack(fill='x',pady=8)
    advanced=ttk.LabelFrame(frame,text='Advanced / optional',padding=8)
    field(advanced,'devkit','Existing devkitPro',True)
    field(advanced,'mesa','Existing Mesa root',True)
    field(advanced,'mesa_archive','Mesa SDK ZIP',types=[('SDK archive','*.zip')])
    field(advanced,'font','Optional shared font',types=[('Personal shared font','*.bin')])
    mesa_mode=tk.StringVar(value='auto')
    mode=ttk.Combobox(advanced,textvariable=mesa_mode,values=['auto','existing','import'],state='readonly');mode.pack(anchor='w');controls.append(mode)
    force_managed=tk.BooleanVar(value=False)
    check=ttk.Checkbutton(advanced,text='Always use a fresh isolated devkitPro installation',variable=force_managed);check.pack(anchor='w');controls.append(check)
    allow_code=tk.BooleanVar(value=False)
    check=ttk.Checkbutton(advanced,text='Experimental: identical executable with different resources (not console validated)',variable=allow_code);check.pack(anchor='w');controls.append(check)
    def emit(**event):
        events.append(event)
        try:messages.put_nowait(event)
        except queue.Full:
            if event.get('stage') in ('complete','error','diagnosed'):messages.put(event)
    def set_busy(value):
        nonlocal active
        active=value
        for c in controls:c.configure(state='disabled' if value else 'normal')
        if not value:mode.configure(state='readonly')
        for c in (build_button,check_button,export_button):c.configure(state='disabled' if value else 'normal')
    def start(build):
        nonlocal last
        if active:return
        values={k:v.get() for k,v in fields.items()}
        if not values['rom']:messagebox.showerror('Choose your dump','Select your personal .3ds or .cci file.',parent=win);return
        if build and not values['output']:messagebox.showerror('Choose an output folder','Select a local output parent.',parent=win);return
        choices=(allow_code.get(),force_managed.get(),mesa_mode.get())
        events.clear();snapshot.clear();set_busy(True)
        def worker():
            nonlocal last
            try:
                emit(stage='validate',message='Reading cartridge metadata and checking executable / partition hashes locally.')
                report=workflow.rom_report(values['rom'],choices[0]);snapshot['rom']=report
                if not report['build_allowed']:
                    emit(stage='error',message=report['message']);return
                if not build:
                    emit(stage='diagnosed',message='Compatible dump verified: '+report['status']+'. Remaster version '+str(report['remaster_version'])+'.');return
                from datetime import datetime
                import secrets
                parent=core.local_path(values['output']);parent.mkdir(parents=True,exist_ok=True)
                last=parent/('ROSA-build-'+datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+secrets.token_hex(2))
                devkit,managed=workflow.choose_dependencies(default_data(),release()['data_sha256'],values['devkit'] or None,choices[1],emit)
                snapshot['result']=core.build(values['rom'],last,devkit,values['mesa'] or None,default_data(),release()['data_sha256'],emit,2,values['font'] or None,managed_sdk=managed,allow_code_equivalent=choices[0],mesa_mode=choices[2],mesa_archive=values['mesa_archive'] or None)
            except Exception as error:
                if hasattr(error,'diagnostic'):snapshot['sdk']=error.diagnostic
                emit(stage='error',message=workflow.explain(error))
        threading.Thread(target=worker,name='rosa-guided-workflow',daemon=False).start()
    check_button=ttk.Button(buttons,text='Diagnose ROM',command=lambda:start(False));check_button.pack(side='left')
    build_button=ttk.Button(buttons,text='Build my port',command=lambda:start(True));build_button.pack(side='left',padx=6)
    def diagnose_sdk():
        if active:return
        values={k:v.get() for k,v in fields.items()};selected_mode=mesa_mode.get();set_busy(True)
        def worker():
            try:
                emit(stage='sdk',message='Checking the authenticated Mesa SDK and selected folder layout.')
                details=workflow.sdk_report(default_data(),release()['data_sha256'],selected_mode,values['mesa'] or None,values['mesa_archive'] or None)
                snapshot['sdk']=details
                emit(stage='diagnosed',message='Mesa SDK verified: exact file hashes and AArch64 objects match. No manual Mesa compilation is needed.')
            except Exception as error:
                if hasattr(error,'diagnostic'):snapshot['sdk']=error.diagnostic
                emit(stage='error',message=workflow.explain(error))
        threading.Thread(target=worker,name='rosa-sdk-diagnostic',daemon=False).start()
    sdk_button=ttk.Button(buttons,text='Diagnose SDK',command=diagnose_sdk);sdk_button.pack(side='left',padx=4);controls.append(sdk_button)
    def export():
        if active:return
        path=filedialog.asksaveasfilename(parent=win,title='Export safe diagnostic (no game or personal paths)',defaultextension='.json',initialfile='ROSA-diagnostic.json',filetypes=[('Diagnostic JSON','*.json')])
        if not path:return
        try:workflow.export_report(path,snapshot.get('rom'),events,snapshot.get('result'),snapshot.get('sdk'));messagebox.showinfo('Report exported','The report contains hashes and stage counters only. Review it before sharing. ROMs, saves, keys, file names, paths and raw logs are excluded.',parent=win)
        except (OSError,core.BuildError):messagebox.showerror('Report preserved','Choose a new local report filename. Existing files are not replaced.',parent=win)
    export_button=ttk.Button(buttons,text='Export diagnostic',command=export);export_button.pack(side='left',padx=6)
    def advanced_toggle():
        if advanced.winfo_manager():advanced.pack_forget();win.geometry('820x710')
        else:advanced.pack(fill='x',pady=8);win.geometry('900x960')
    ttk.Button(buttons,text='Advanced',command=advanced_toggle).pack(side='left')
    def open_output():
        if last and last.exists() and hasattr(os,'startfile'):os.startfile(last)
    ttk.Button(frame,text='Open latest output',command=open_output).pack(anchor='w')
    def notices():
        try:
            if core.sha(default_data())!=release()['data_sha256']:raise core.BuildError('DATA integrity')
            with zipfile.ZipFile(default_data()) as archive:notice=archive.read('licenses/NOTICE.txt').decode('utf-8')
        except Exception:messagebox.showerror('Notices unavailable','Restore the matching EXE/DATA pair.',parent=win);return
        dialog=tk.Toplevel(win);dialog.title('Third-party notices');dialog.geometry('740x450')
        area=tk.Text(dialog,wrap='word');area.pack(fill='both',expand=True)
        area.insert('1.0',notice);area.configure(state='disabled')
    ttk.Button(frame,text='Licenses / source notices',command=notices).pack(anchor='w')

    ttk.Label(frame,text='First launch in a new area can compile shaders. Known shaders can be reused on relaunch.\nDo not share generated code, NROs, dumps, saves or private shader packs. Console validation remains separate.',wraplength=740).pack(anchor='w',pady=10)
    def poll():
        try:
            while True:
                event=messages.get_nowait();stage=event['stage'];state.set(event['message']);bar.stop()
                target='compile' if stage in ('generate','link','copy','stage') else stage
                if target in steps:steps[target].set(event['message'])
                if stage in ('validate','sdk','generate','link'):bar.configure(mode='indeterminate');bar.start(15)
                else:bar.configure(mode='determinate',maximum=event.get('total',1),value=event.get('done',0))
                if stage in ('complete','error','diagnosed'):
                    set_busy(False);bar.stop()
                    if stage=='complete':messagebox.showinfo('PC build complete','The new SD folder is ready for a controlled console test. No SD/NAND installation was performed.',parent=win)
        except queue.Empty:pass
        win.after(100,poll)
    def close():
        if active:messagebox.showinfo('Operation in progress','Wait for the current operation; compiler processes must finish safely.',parent=win)
        else:win.destroy()
    win.protocol('WM_DELETE_WINDOW',close);poll()
    if '--ui-smoke-report' in sys.argv:
        dest=Path(sys.argv[sys.argv.index('--ui-smoke-report')+1])
        def smoke():
            win.update_idletasks()
            with dest.open('x') as f:json.dump({'title':win.title(),'fields':list(fields),'automatic_dependencies_default':True,'diagnostic_button':True,'sdk_diagnostic_button':True,'export_button':True,'advanced_hidden':not bool(advanced.winfo_manager()),'visual_validation':False},f,indent=2)
            win.destroy()
        win.after(250,smoke)
    win.mainloop()

if __name__=='__main__':
    if '--cli' in sys.argv:sys.exit(cli())
    gui()
