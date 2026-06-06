elif menu == "📆 Cronograma Impresión":
    import streamlit.components.v1 as components
    import json

    st.markdown("<div class='title-area'>📆 CRONOGRAMA DE IMPRESIÓN</div>", unsafe_allow_html=True)
    st.caption("Arrastra las tarjetas de la derecha al cronograma. Mueve o estira los bloques para ajustar. Todo se guarda solo.")

    lista_maquinas = ["ATF-22", "HR-22", "HAMILTON", "HR-17", "DIDDE 11", "MULTILYTH 1", "MULTILYTH 2"]

    # Capturar cambios enviados desde el HTML via query_params
    qp = st.query_params
    if "crono_id" in qp:
        try:
            supabase.table("ordenes_planeadas").update({
                "fecha_inicio_cronograma": qp["crono_start"],
                "fecha_fin_cronograma":    qp["crono_end"],
                "maquina_cronograma":      qp["crono_maq"]
            }).eq("id", qp["crono_id"]).execute()
        except:
            pass
        st.query_params.clear()
        st.rerun()

    try:
        todas_las_ops = supabase.table("ordenes_planeadas").select("*").execute().data or []
    except:
        todas_las_ops = []

    ops_agendadas  = [op for op in todas_las_ops if op.get("fecha_inicio_cronograma") and op.get("fecha_fin_cronograma") and op.get("maquina_cronograma")]
    ops_pendientes = [op for op in todas_las_ops if not (op.get("fecha_inicio_cronograma") and op.get("maquina_cronograma")) and op.get("estado") != "Terminado"]

    # Eventos agendados para el calendario
    eventos_json = []
    for op in ops_agendadas:
        color = "#4a4a4a" if op.get("proxima_area") == "FINALIZADO" else ("#2563eb" if op.get("estado") == "En Proceso" else "#d97706")
        eventos_json.append({
            "id":              str(op["id"]),
            "resourceId":      op["maquina_cronograma"],
            "title":           f"OP {op.get('op','?')} · {op.get('cliente','')[:14]}",
            "start":           op["fecha_inicio_cronograma"],
            "end":             op["fecha_fin_cronograma"],
            "backgroundColor": color,
            "borderColor":     color,
            "textColor":       "#ffffff",
            "extendedProps":   {"cliente": op.get("cliente",""), "estado": op.get("estado",""), "db_id": str(op["id"])}
        })

    # OPs pendientes como tarjetas arrastrables (eventos externos)
    pendientes_json = []
    for op in ops_pendientes:
        pendientes_json.append({
            "id":    str(op["id"]),
            "title": f"OP {op.get('op','?')} · {op.get('cliente','')[:14]}",
            "extendedProps": {"cliente": op.get("cliente",""), "db_id": str(op["id"])}
        })

    recursos_json  = [{"id": m, "title": m} for m in lista_maquinas]
    eventos_str    = json.dumps(eventos_json,   ensure_ascii=False)
    recursos_str   = json.dumps(recursos_json,  ensure_ascii=False)
    pendientes_str = json.dumps(pendientes_json, ensure_ascii=False)

    # URL base para el puente query_params
    try:
        base_url = st.secrets.get("APP_URL", "https://planta-online.streamlit.app")
    except:
        base_url = "https://planta-online.streamlit.app"

    html_cronograma = """
    <!DOCTYPE html><html>
    <head>
      <link href='https://cdn.jsdelivr.net/npm/fullcalendar-scheduler@6.1.11/index.global.min.css' rel='stylesheet'/>
      <script src='https://cdn.jsdelivr.net/npm/fullcalendar-scheduler@6.1.11/index.global.min.js'></script>
      <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { background: #191919; color: #e0e0e0; font-family: 'Segoe UI', sans-serif; display: flex; gap: 10px; padding: 10px; }
        #calendar-wrap { flex: 1; min-width: 0; }
        #sidebar {
          width: 190px; flex-shrink: 0; background: #1f1f1f;
          border: 1px solid #2e2e2e; border-radius: 10px; padding: 10px;
          display: flex; flex-direction: column; gap: 6px; overflow-y: auto; max-height: 560px;
        }
        #sidebar h3 { color: #aaa; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 4px; }
        .tarjeta {
          background: #2a2a2a; border: 1px solid #3a3a3a; border-radius: 8px;
          padding: 8px 10px; font-size: 12px; cursor: grab; color: #e0e0e0;
          transition: background 0.15s;
        }
        .tarjeta:hover { background: #333; border-color: #d97706; }
        .tarjeta .op-num { font-weight: 700; color: #d97706; font-size: 13px; }
        .tarjeta .cli { color: #aaa; font-size: 11px; margin-top: 2px; }
        .no-pending { color: #555; font-size: 12px; text-align: center; margin-top: 20px; }
        .fc .fc-toolbar { background: #191919; padding: 8px 0; border-bottom: 1px solid #2e2e2e; }
        .fc .fc-toolbar-title { color: #e0e0e0; font-size: 15px; font-weight: 600; }
        .fc .fc-button { background: #2e2e2e !important; border: 1px solid #3e3e3e !important; color: #ccc !important; border-radius: 6px !important; font-size: 12px !important; padding: 4px 10px !important; }
        .fc .fc-button:hover { background: #3a3a3a !important; }
        .fc .fc-button-active { background: #444 !important; }
        .fc .fc-col-header-cell { background: #1f1f1f; border-color: #2e2e2e; }
        .fc .fc-col-header-cell-cushion { color: #aaa; font-size: 11px; text-decoration: none; padding: 5px; }
        .fc-datagrid-cell { background: #1f1f1f !important; border-color: #2a2a2a !important; }
        .fc .fc-datagrid-cell-cushion { color: #ccc; font-size: 12px; font-weight: 600; }
        .fc-timeline-slot { border-color: #2a2a2a !important; }
        .fc-timeline-lane { border-color: #2a2a2a !important; background: #191919; }
        .fc-event { border-radius: 6px !important; border: none !important; padding: 3px 7px !important; font-size: 12px !important; cursor: grab !important; }
        .fc-event:hover { filter: brightness(1.2); }
        .fc .fc-timeline-now-indicator-line { border-color: #ef4444; }
        #toast {
          display: none; position: fixed; bottom: 18px; left: 50%; transform: translateX(-50%);
          background: #22c55e; color: #fff; padding: 8px 20px; border-radius: 20px;
          font-size: 13px; font-weight: 600; z-index: 9999; box-shadow: 0 4px 15px rgba(0,0,0,0.4);
        }
        #tooltip {
          display: none; position: fixed; background: #2a2a2a; border: 1px solid #444;
          color: #eee; padding: 10px 14px; border-radius: 8px; font-size: 12px;
          z-index: 9998; pointer-events: none; max-width: 220px; line-height: 1.7;
        }
      </style>
    </head>
    <body>
      <div id="calendar-wrap"><div id="calendar"></div></div>
      <div id="sidebar">
        <h3>📋 Sin asignar</h3>
        <div id="lista-pendientes"></div>
      </div>
      <div id="toast">✅ Guardado</div>
      <div id="tooltip"></div>
      <script>
        var eventos    = """ + eventos_str    + """;
        var recursos   = """ + recursos_str   + """;
        var pendientes = """ + pendientes_str + """;
        var BASE_URL   = """ + json.dumps(base_url) + """;
        var tooltip    = document.getElementById('tooltip');
        var toast      = document.getElementById('toast');

        // Mostrar toast brevemente
        function showToast(msg) {
          toast.textContent = msg;
          toast.style.display = 'block';
          setTimeout(function() { toast.style.display = 'none'; }, 2000);
        }

        // Guardar cambio en Supabase via query_params (recarga Streamlit)
        function guardarEnSupabase(db_id, start, end, maquina) {
          var url = BASE_URL + '?crono_id=' + encodeURIComponent(db_id)
                             + '&crono_start=' + encodeURIComponent(start)
                             + '&crono_end='   + encodeURIComponent(end)
                             + '&crono_maq='   + encodeURIComponent(maquina);
          showToast('💾 Guardando...');
          window.parent.location.href = url;
        }

        document.addEventListener('mousemove', function(e) {
          tooltip.style.left = (e.clientX + 15) + 'px';
          tooltip.style.top  = (e.clientY + 10) + 'px';
        });

        document.addEventListener('DOMContentLoaded', function() {
          // Renderizar tarjetas arrastrables en sidebar
          var lista = document.getElementById('lista-pendientes');
          if (pendientes.length === 0) {
            lista.innerHTML = '<div class="no-pending">🎉 Todas programadas</div>';
          } else {
            pendientes.forEach(function(p) {
              var div = document.createElement('div');
              div.className = 'tarjeta';
              div.setAttribute('data-event', JSON.stringify({
                id: p.id,
                title: p.title,
                duration: '02:00',
                backgroundColor: '#d97706',
                borderColor: '#d97706',
                textColor: '#fff',
                extendedProps: p.extendedProps
              }));
              div.innerHTML = '<div class="op-num">' + p.title.split('·')[0].trim() + '</div>'
                            + '<div class="cli">👤 ' + p.extendedProps.cliente + '</div>';
              lista.appendChild(div);
            });
          }

          var calEl = document.getElementById('calendar');
          var cal = new FullCalendar.Calendar(calEl, {
            schedulerLicenseKey: 'CC-Attribution-NonCommercial-NoDerivatives',
            initialView:  'resourceTimelineDay',
            locale:       'es',
            height:       560,
            nowIndicator: true,
            editable:     true,
            droppable:    true,
            eventResizableFromStart: true,
            slotDuration: '01:00:00',
            slotLabelFormat: { hour: '2-digit', minute: '2-digit', hour12: false },
            scrollTime:   '06:00:00',
            resourceAreaWidth: '13%',
            resourceAreaHeaderContent: 'Máquina',
            headerToolbar: {
              left:   'prev,next today',
              center: 'title',
              right:  'resourceTimelineDay,resourceTimelineWeek,resourceTimelineMonth'
            },
            buttonText: { today: 'Hoy', day: 'Día', week: 'Semana', month: 'Mes' },
            resources: recursos,
            events:    eventos,

            // Al soltar una tarjeta externa en el calendario
            drop: function(info) {
              info.draggedEl.parentNode.removeChild(info.draggedEl);
            },
            eventReceive: function(info) {
              var ev    = info.event;
              var db_id = ev.extendedProps.db_id;
              var maq   = ev.getResources()[0] ? ev.getResources()[0].id : '';
              var start = ev.start ? ev.start.toISOString() : '';
              var end   = ev.end   ? ev.end.toISOString()   : '';
              if (!end) {
                var tmp = new Date(ev.start);
                tmp.setHours(tmp.getHours() + 2);
                end = tmp.toISOString();
              }
              guardarEnSupabase(db_id, start, end, maq);
            },

            // Al mover o redimensionar un evento ya en el calendario
            eventChange: function(info) {
              var ev    = info.event;
              var db_id = ev.extendedProps.db_id || ev.id;
              var maq   = ev.getResources()[0] ? ev.getResources()[0].id : '';
              var start = ev.start ? ev.start.toISOString() : '';
              var end   = ev.end   ? ev.end.toISOString()   : '';
              guardarEnSupabase(db_id, start, end, maq);
            },

            // Tooltip hover
            eventMouseEnter: function(info) {
              var p = info.event.extendedProps;
              var s = info.event.start ? info.event.start.toLocaleString('es-CO', {hour:'2-digit', minute:'2-digit', day:'2-digit', month:'short'}) : '';
              var e = info.event.end   ? info.event.end.toLocaleString('es-CO',   {hour:'2-digit', minute:'2-digit', day:'2-digit', month:'short'}) : '';
              tooltip.innerHTML = '<b style="color:#fff">' + info.event.title + '</b><br>👤 ' + p.cliente + '<br>📌 ' + p.estado + '<br>🕐 ' + s + '<br>🏁 ' + e;
              tooltip.style.display = 'block';
            },
            eventMouseLeave: function() { tooltip.style.display = 'none'; }
          });
          cal.render();

          // Activar drag desde las tarjetas del sidebar
          new FullCalendar.ThirdPartyDraggable(document.getElementById('lista-pendientes'), {
            itemSelector: '.tarjeta',
            eventData: function(el) {
              return JSON.parse(el.getAttribute('data-event'));
            }
          });
        });
      </script>
    </body>
    </html>
    """ 

    components.html(html_cronograma, height=620, scrolling=False)
